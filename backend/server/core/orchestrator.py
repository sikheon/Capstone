import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from .. import algorithms, models, datasets, selection
from ..config import config
from .client_manager import ClientManager
from .weights import from_jsonable


@dataclass
class RoundState:
    round_num: int
    started_at: float
    selected: list[str]
    received: dict[str, dict[str, Any]] = field(default_factory=dict)
    finished_at: float | None = None
    aggregated_at: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """Drives FL in either **sync** mode (round-based) or **async** mode
    (continuous, MQTT-style: clients post updates whenever, server blends them
    into the global model on the fly).

    Both modes share the same swappable components — algorithm / model /
    dataset / selection / dropout. The web UI picks the mode at start time."""

    def __init__(self, clients: ClientManager) -> None:
        self.clients = clients
        self.algorithm = algorithms.get(config.algorithm)
        self.model = models.get(config.model)
        self.dataset = datasets.get(config.dataset)
        self.selection = selection.get(config.selection)
        self.global_weights = self.model.initial_weights()
        self.round: RoundState | None = None
        self.history: list[RoundState] = []
        self._running = False
        self._paused = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._on_event: Callable[[str, dict], None] | None = None
        # async-mode bookkeeping
        self._async_round = 0
        self._last_submit_at: dict[str, float] = {}
        # held-out evaluation of the global model
        from .evaluator import GlobalEvaluator
        self.evaluator = GlobalEvaluator()
        self._eval_every_rounds = 1
        self._async_eval_every_updates = 5
        self._async_update_count = 0

    # ---- glue ----
    def attach(self, loop: asyncio.AbstractEventLoop, on_event) -> None:
        self._loop = loop
        self._on_event = on_event

    # ---- runtime swap (apply on the next round / next submit) ----
    def set_algorithm(self, name: str) -> None:
        self.algorithm = algorithms.get(name); config.algorithm = name

    def set_model(self, name: str) -> None:
        self.model = models.get(name)
        self.global_weights = self.model.initial_weights()
        config.model = name

    def set_dataset(self, name: str) -> None:
        self.dataset = datasets.get(name); config.dataset = name

    def set_selection(self, name: str) -> None:
        self.selection = selection.get(name); config.selection = name

    # ---- lifecycle ----
    def state(self) -> str:
        if not self._running: return "stopped"
        if self._paused: return "paused"
        return "running"

    def start(self, mode: str = "sync") -> bool:
        # Reject if a previous run hasn't yielded its task yet — avoids two
        # concurrent loops driving the same global_weights.
        if self._running or (self._task and not self._task.done()):
            return False
        if mode not in ("sync", "async"):
            raise ValueError(f"unknown mode: {mode}")
        if self._loop is None:
            raise RuntimeError("orchestrator not attached to an event loop")
        config.mode = mode
        self._running = True
        self._paused = False
        coro = self._run_async() if mode == "async" else self._run_sync()
        self._task = self._loop.create_task(coro)
        self._emit("orchestrator_started", {"mode": mode})
        return True

    def pause(self) -> None:
        self._paused = True
        self._emit("orchestrator_paused", {})

    def resume(self) -> None:
        self._paused = False
        self._emit("orchestrator_resumed", {})

    def stop(self) -> None:
        self._running = False
        self._emit("orchestrator_stopped", {})

    def _emit(self, event: str, payload: dict) -> None:
        if self._on_event:
            self._on_event(event, payload)

    # ---- sync mode ----
    async def _run_sync(self) -> None:
        r = 0
        while r < config.total_rounds and self._running:
            if self._paused:
                await asyncio.sleep(1); continue
            await self._run_round(r)
            r += 1
        self._running = False

    async def _run_round(self, round_num: int) -> None:
        active = [c for c in self.clients.all() if c.active]
        if len(active) < config.min_clients_per_round:
            await asyncio.sleep(2); return

        selected_ids = self.selection.select(
            active, round_num, config.client_fraction, config.min_clients_per_round
        )
        if config.auto_dropout_control:
            risky = {c.client_id for c in active if c.dropout_risk >= config.dropout_threshold}
            selected_ids = [cid for cid in selected_ids if cid not in risky]
        if len(selected_ids) < config.min_clients_per_round:
            await asyncio.sleep(2); return

        self.round = RoundState(round_num=round_num, started_at=time.time(), selected=selected_ids)
        self._emit("round_started", {
            "round": round_num, "selected": selected_ids,
            "algorithm": config.algorithm, "model": config.model,
            "selection": config.selection, "local_epochs": config.local_epochs,
            "mode": "sync",
        })

        deadline = time.time() + config.round_timeout_sec
        while time.time() < deadline and len(self.round.received) < len(selected_ids):
            if not self._running: return
            await asyncio.sleep(0.5)

        if self.round.received:
            updates = list(self.round.received.values())
            self.global_weights = self.algorithm.aggregate(updates, self.global_weights)
            self.round.aggregated_at = time.time()
            tot = sum(u["num_samples"] for u in updates) or 1
            avg_loss = sum(u["metrics"].get("loss", 0.0) * u["num_samples"] for u in updates) / tot
            avg_acc = sum(u["metrics"].get("accuracy", 0.0) * u["num_samples"] for u in updates) / tot
            self.round.metrics = {"loss": float(avg_loss), "accuracy": float(avg_acc),
                                  "participants": len(updates), "samples": int(tot)}

        # ---- evaluate the new global model on held-out data ----
        if self.round.received and round_num % self._eval_every_rounds == 0:
            try:
                ev = self.evaluator.evaluate(self.global_weights, config.model, round_num,
                                             dataset=config.dataset)
                self.round.metrics["test_loss"] = ev["test_loss"]
                self.round.metrics["test_accuracy"] = ev["test_accuracy"]
                self._emit("global_eval", ev)
            except Exception as e:
                self._emit("global_eval_error", {"error": str(e)})

        self.round.finished_at = time.time()
        self.history.append(self.round)
        self._emit("round_finished", {
            "round": round_num,
            "received": list(self.round.received),
            "duration": self.round.finished_at - self.round.started_at,
            "metrics": self.round.metrics,
            "mode": "sync",
        })

    # ---- async mode (continuous, MQTT-style) ----
    async def _run_async(self) -> None:
        """No round boundaries. Clients can submit updates at any time and
        each contribution is blended into the global model immediately
        (FedAsync-flavored). We still emit periodic 'pulse' events so the
        dashboard has something to plot."""
        self._emit("async_started", {"blend": config.async_blend})
        while self._running:
            if self._paused:
                await asyncio.sleep(1); continue
            await asyncio.sleep(2.0)
            self._emit("async_pulse", {
                "active": len([c for c in self.clients.all() if c.active]),
                "global_step": self._async_round,
            })
        self._running = False

    # ---- update intake (shared by both modes) ----
    def submit_update(self, client_id: str, weights: dict,
                      num_samples: int, metrics: dict | None = None) -> bool:
        if config.mode == "async":
            now = time.time()
            last = self._last_submit_at.get(client_id, 0.0)
            if now - last < config.async_min_interval_sec:
                return False
            self._last_submit_at[client_id] = now

            client_w = from_jsonable(weights)
            blend = config.async_blend
            new_global: dict = {}
            for k, gv in self.global_weights.items():
                gv_arr = np.asarray(gv, dtype=np.float32)
                cv = client_w.get(k, gv_arr).reshape(gv_arr.shape)
                new_global[k] = ((1.0 - blend) * gv_arr + blend * cv).astype(np.float32)
            self.global_weights = new_global
            self._async_round += 1
            self._async_update_count += 1
            rs = RoundState(round_num=self._async_round, started_at=now,
                            selected=[client_id])
            rs.received[client_id] = {"client_id": client_id, "weights": weights,
                                      "num_samples": num_samples, "metrics": metrics or {}}
            rs.finished_at = time.time()
            rs.aggregated_at = rs.finished_at
            self.round = rs  # so /api/status surfaces the current async step
            if self._async_update_count % self._async_eval_every_updates == 0:
                try:
                    ev = self.evaluator.evaluate(self.global_weights, config.model, self._async_round,
                                                 dataset=config.dataset)
                    self._emit("global_eval", ev)
                except Exception as e:
                    import traceback
                    self._emit("global_eval_error", {"error": str(e), "trace": traceback.format_exc()})
                    print(f"[eval] failed: {e}\n{traceback.format_exc()}")
            rs.metrics = {
                "loss": float((metrics or {}).get("loss", 0.0)),
                "accuracy": float((metrics or {}).get("accuracy", 0.0)),
                "participants": 1, "samples": int(num_samples),
            }
            self.history.append(rs)
            self._emit("async_update", {"round": rs.round_num, "client_id": client_id,
                                        "metrics": rs.metrics})
            return True

        # sync mode: gather into the current round
        if not self.round or client_id not in self.round.selected:
            return False
        self.round.received[client_id] = {
            "client_id": client_id, "weights": weights,
            "num_samples": num_samples, "metrics": metrics or {},
        }
        return True

    def metric_history(self) -> list[dict]:
        return [{"round": r.round_num, **r.metrics} for r in self.history if r.metrics]
