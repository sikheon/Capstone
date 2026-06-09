"""Benchmark control plane. Admin-gated: triggering experiments would be a
denial-of-service if open to everyone."""

import threading
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .rest import require_admin
from ..benchmark import BenchmarkRunner, BenchmarkStore
from ..benchmark.runner import Scenario


class ScenarioIn(BaseModel):
    name: str
    algorithm: str = "fedavg"
    selection: str = "all"
    iid: bool = True
    dropout_rate: float = 0.0
    num_clients: int = 8
    rounds: int = 20
    local_epochs: int = 1
    batch_size: int = 32
    client_fraction: float = 1.0
    min_clients: int = 2
    seed: int = 0


class MatrixIn(BaseModel):
    """Submit a cross-product of scenarios with one POST."""
    base: ScenarioIn
    selection_options: list[str] | None = None      # e.g. ["all","random","dropout_aware"]
    iid_options: list[bool] | None = None           # [True, False]
    dropout_rates: list[float] | None = None        # [0.0, 0.3, 0.5]


def make_router(runner: BenchmarkRunner, store: BenchmarkStore, bus) -> APIRouter:
    router = APIRouter()

    def _kick(scenario: Scenario) -> dict:
        def _run():
            def on_progress(res):
                bus.publish("benchmark_progress", {
                    "id": res.id,
                    "round": len(res.rounds),
                    "scenario": res.scenario,
                    "latest": res.rounds[-1] if res.rounds else None,
                })
            res = runner.run(scenario, on_progress=on_progress)
            store.save(res)
            bus.publish("benchmark_finished", {
                "id": res.id, "status": res.status,
                "final_test_accuracy": res.final_test_accuracy,
                "final_test_loss": res.final_test_loss,
            })
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return {"ok": True, "scenario": scenario.asdict()}

    @router.post("/benchmark/run", dependencies=[Depends(require_admin)])
    def run_one(body: ScenarioIn):
        return _kick(Scenario(**body.model_dump()))

    @router.post("/benchmark/matrix", dependencies=[Depends(require_admin)])
    def run_matrix(body: MatrixIn):
        base = body.base.model_dump()
        selections = body.selection_options or [base["selection"]]
        iids = body.iid_options if body.iid_options is not None else [base["iid"]]
        drops = body.dropout_rates or [base["dropout_rate"]]
        scheduled = []
        for sel in selections:
            for iid in iids:
                for d in drops:
                    s = {**base,
                         "selection": sel,
                         "iid": iid,
                         "dropout_rate": d,
                         "name": f"{base['name']} · sel={sel} · iid={iid} · drop={int(d*100)}%"}
                    _kick(Scenario(**s))
                    scheduled.append(s["name"])
        return {"ok": True, "scheduled": scheduled, "count": len(scheduled)}

    @router.get("/benchmark/results")
    def list_results():
        return store.list()

    @router.get("/benchmark/{run_id}")
    def get_result(run_id: str):
        r = store.get(run_id)
        if not r: raise HTTPException(404, "not found")
        return r.asdict()

    @router.delete("/benchmark/{run_id}", dependencies=[Depends(require_admin)])
    def delete_result(run_id: str):
        ok = store.delete(run_id)
        if not ok: raise HTTPException(404, "not found")
        return {"ok": True}

    return router
