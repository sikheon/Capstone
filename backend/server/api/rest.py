from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .. import algorithms, models, datasets, selection, dropout as dropout_mod
from ..auth import auth
from ..config import config
from ..core.weights import to_jsonable

router = APIRouter()


# -------- request models --------

class RegisterIn(BaseModel):
    client_id: str
    kind: str = "edge"
    os: str | None = None
    arch: str | None = None
    hostname: str | None = None
    model_hw: str | None = None
    app_version: str | None = None
    metadata: dict | None = None


class HeartbeatIn(BaseModel):
    client_id: str
    kind: str = "edge"
    battery: float | None = None
    charging: bool | None = None
    network: str | None = None
    cpu_load: float | None = None


class UpdateIn(BaseModel):
    client_id: str
    weights: dict
    num_samples: int
    metrics: dict | None = None


class SwapIn(BaseModel):
    name: str


class StartIn(BaseModel):
    mode: str = "sync"  # "sync" | "async"


class LoginIn(BaseModel):
    username: str
    password: str


class ProvisionIn(BaseModel):
    suggested_id: str | None = None


class ParamsIn(BaseModel):
    total_rounds: int | None = None
    min_clients_per_round: int | None = None
    client_fraction: float | None = None
    round_timeout_sec: int | None = None
    local_epochs: int | None = None
    dropout_threshold: float | None = None
    auto_dropout_control: bool | None = None


# -------- auth dependencies --------

def require_admin(authorization: str | None = Header(None)) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not auth.verify_admin(token):
        raise HTTPException(401, "admin auth required")


def require_client(
    x_client_id: str | None = Header(None),
    x_client_secret: str | None = Header(None),
) -> str:
    if not auth.verify_client(x_client_id, x_client_secret):
        raise HTTPException(401, "client auth required")
    return x_client_id  # type: ignore[return-value]


def make_router(orchestrator, clients, advisor):
    # -------- public --------

    @router.get("/status")
    def status():
        return {
            "algorithm": config.algorithm,
            "model": config.model,
            "dataset": config.dataset,
            "selection": config.selection,
            "dropout_predictor": advisor.name,
            "round": orchestrator.round.round_num if orchestrator.round else None,
            "history_len": len(orchestrator.history),
            "clients": len(clients.all()),
            "orchestrator_state": orchestrator.state(),
        }

    @router.get("/rounds")
    def rounds():
        return [
            {
                "round": r.round_num,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "duration": (r.finished_at - r.started_at) if r.finished_at else None,
                "selected": r.selected,
                "received": list(r.received),
                "metrics": r.metrics,
            }
            for r in orchestrator.history
        ]

    @router.get("/global_model")
    def global_model():
        """Performance of the current global model on the held-out test set."""
        ev = orchestrator.evaluator
        return {
            "current": ev.last,
            "history": ev.history,
            "model": config.model,
            "evaluated_count": len(ev.history),
        }

    @router.get("/registry")
    def registry():
        return {
            "algorithms": algorithms.available(),
            "models": models.available(),
            "datasets": datasets.available(),
            "selection": selection.available(),
            "dropout": dropout_mod.available(),
        }

    @router.get("/metrics")
    def metrics():
        return orchestrator.metric_history()

    @router.get("/params")
    def get_params():
        return {
            "total_rounds": config.total_rounds,
            "min_clients_per_round": config.min_clients_per_round,
            "client_fraction": config.client_fraction,
            "round_timeout_sec": config.round_timeout_sec,
            "local_epochs": config.local_epochs,
            "dropout_threshold": config.dropout_threshold,
            "auto_dropout_control": config.auto_dropout_control,
        }

    @router.get("/clients")
    def list_clients():
        out = []
        for s in clients.all():
            d = advisor.evaluate(s)
            out.append({
                "client_id": s.client_id, "kind": s.kind, "active": s.active,
                "os": s.os, "arch": s.arch, "hostname": s.hostname,
                "model_hw": s.model_hw, "app_version": s.app_version,
                "registered_at": s.registered_at,
                "battery": s.battery, "charging": s.charging, "network": s.network,
                "cpu_load": s.cpu_load, "last_seen": s.last_seen,
                "banned": auth.is_banned(s.client_id),
                "dropout": d,
            })
        return out

    # -------- admin auth --------

    @router.post("/admin/login")
    def login(body: LoginIn):
        token = auth.admin_login(body.username, body.password)
        if not token:
            raise HTTPException(401, "invalid credentials")
        return {"token": token, "ttl_sec": auth.token_ttl_sec}

    @router.post("/admin/logout", dependencies=[Depends(require_admin)])
    def logout(authorization: str | None = Header(None)):
        token = (authorization or "").removeprefix("Bearer ").strip()
        auth.admin_logout(token)
        return {"ok": True}

    # -------- admin-only mutations --------

    @router.patch("/params", dependencies=[Depends(require_admin)])
    def patch_params(body: ParamsIn):
        for k, v in body.model_dump(exclude_none=True).items():
            setattr(config, k, v)
        return get_params()

    @router.post("/algorithm", dependencies=[Depends(require_admin)])
    def swap_algorithm(body: SwapIn):
        try: orchestrator.set_algorithm(body.name)
        except KeyError as e: raise HTTPException(404, str(e))
        return {"ok": True, "algorithm": body.name}

    @router.post("/model", dependencies=[Depends(require_admin)])
    def swap_model(body: SwapIn):
        try: orchestrator.set_model(body.name)
        except KeyError as e: raise HTTPException(404, str(e))
        return {"ok": True, "model": body.name}

    @router.post("/dataset", dependencies=[Depends(require_admin)])
    def swap_dataset(body: SwapIn):
        try: orchestrator.set_dataset(body.name)
        except KeyError as e: raise HTTPException(404, str(e))
        return {"ok": True, "dataset": body.name}

    @router.post("/selection", dependencies=[Depends(require_admin)])
    def swap_selection(body: SwapIn):
        try: orchestrator.set_selection(body.name)
        except KeyError as e: raise HTTPException(404, str(e))
        return {"ok": True, "selection": body.name}

    @router.post("/dropout", dependencies=[Depends(require_admin)])
    def swap_dropout(body: SwapIn):
        try: advisor.set(body.name)
        except KeyError as e: raise HTTPException(404, str(e))
        return {"ok": True, "dropout_predictor": body.name}

    @router.post("/admin/round/start", dependencies=[Depends(require_admin)])
    def round_start(body: StartIn):
        ok = orchestrator.start(body.mode)
        return {"ok": ok, "state": orchestrator.state(), "mode": body.mode}

    @router.post("/admin/round/pause", dependencies=[Depends(require_admin)])
    def round_pause():
        orchestrator.pause()
        return {"ok": True, "state": orchestrator.state()}

    @router.post("/admin/round/resume", dependencies=[Depends(require_admin)])
    def round_resume():
        orchestrator.resume()
        return {"ok": True, "state": orchestrator.state()}

    @router.post("/admin/round/stop", dependencies=[Depends(require_admin)])
    def round_stop():
        orchestrator.stop()
        return {"ok": True, "state": orchestrator.state()}

    @router.post("/admin/kick/{client_id}", dependencies=[Depends(require_admin)])
    def kick(client_id: str):
        clients.deactivate(client_id)
        auth.revoke_client(client_id)
        return {"ok": True, "client_id": client_id, "action": "kicked"}

    @router.post("/admin/ban/{client_id}", dependencies=[Depends(require_admin)])
    def ban(client_id: str):
        clients.deactivate(client_id)
        auth.ban_client(client_id)
        return {"ok": True, "client_id": client_id, "action": "banned"}

    @router.post("/admin/unban/{client_id}", dependencies=[Depends(require_admin)])
    def unban(client_id: str):
        auth.unban_client(client_id)
        return {"ok": True, "client_id": client_id, "action": "unbanned"}

    @router.get("/admin/banned", dependencies=[Depends(require_admin)])
    def banned():
        return {"banned": auth.banned_list()}

    # -------- client provisioning + telemetry --------

    @router.post("/provision")
    def provision(body: ProvisionIn):
        try:
            cid, secret = auth.provision_client(body.suggested_id)
        except PermissionError:
            raise HTTPException(403, "client_id is banned")
        return {"client_id": cid, "client_secret": secret}

    @router.post("/register")
    def register(body: RegisterIn, _cid: str = Depends(require_client)):
        import time as _t
        if body.client_id != _cid:
            raise HTTPException(403, "client_id mismatch with credentials")
        payload = body.model_dump()
        meta = payload.pop("metadata", None) or {}
        s = clients.upsert(**payload)
        s.registered_at = _t.time()
        for k, v in meta.items():
            s.metadata[k] = v
        return {"ok": True, "client_id": s.client_id, "kind": s.kind}

    @router.post("/heartbeat")
    def heartbeat(body: HeartbeatIn, _cid: str = Depends(require_client)):
        if body.client_id != _cid:
            raise HTTPException(403, "client_id mismatch with credentials")
        s = clients.upsert(**body.model_dump())
        s.dropout_risk = advisor.evaluate(s)["risk"]
        round_num = orchestrator.round.round_num if orchestrator.round else None
        selected = bool(orchestrator.round and _cid in orchestrator.round.selected)
        return {
            "ok": True,
            "dropout_risk": s.dropout_risk,
            # FL session info — lets the client UI react to "admin started FL"
            "orchestrator_state": orchestrator.state(),
            "mode": config.mode,
            "round": round_num,
            "selected_for_round": selected,
            "algorithm": config.algorithm,
            "model": config.model,
            "dataset": config.dataset,
            "local_epochs": config.local_epochs,
        }

    @router.post("/update")
    def submit_update(body: UpdateIn, _cid: str = Depends(require_client)):
        if body.client_id != _cid:
            raise HTTPException(403, "client_id mismatch with credentials")
        ok = orchestrator.submit_update(body.client_id, body.weights, body.num_samples, body.metrics)
        if not ok:
            raise HTTPException(400, "client not part of current round")
        return {"ok": True}

    @router.get("/dataset/{name}/sample")
    def dataset_sample(name: str, n: int = 200, _cid: str = Depends(require_client)):
        """Server pushes a deterministic per-client slice of the dataset to the
        device. The device caches it and uses it for local training/eval."""
        try:
            spec = datasets.get(name)
        except KeyError as e:
            raise HTTPException(404, str(e))
        bundle = spec.sample(n=n, client_id=_cid)
        if bundle is None:
            raise HTTPException(501, f"dataset '{name}' does not expose .sample()")
        return bundle

    @router.get("/round/current")
    def current_round(_cid: str = Depends(require_client)):
        """Client fetches this when heartbeat says it has been selected. Returns
        the global weights it should fine-tune locally."""
        return {
            "round": orchestrator.round.round_num if orchestrator.round else None,
            "mode": config.mode,
            "local_epochs": config.local_epochs,
            "algorithm": config.algorithm,
            "model": config.model,
            "dataset": config.dataset,
            "selected_for_round": bool(orchestrator.round and _cid in orchestrator.round.selected),
            "weights": to_jsonable(orchestrator.global_weights),
        }

    return router
