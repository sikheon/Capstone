"""In-process FL benchmark runner.

Instead of spinning up real clients, we simulate the entire round loop here:
  - load MNIST once
  - partition into client shards (IID or non-IID)
  - each round, the selection policy picks participants
  - simulate dropout (configurable fraction of selected clients fail to submit)
  - remaining clients run a few local SGD steps on their shard
  - aggregate via the chosen algorithm, evaluate on the held-out test set

This sidesteps networking / authentication entirely so a 18-cell matrix runs
in single-digit minutes instead of hours."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Callable

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from .. import algorithms, selection
from ..core.client_manager import ClientState
from ..core.weights import to_jsonable
from ..datasets import _idx_io
from ..models.cnn_mnist import CnnMnistModule


# --------- scenario spec ----------

@dataclass
class Scenario:
    name: str
    algorithm: str = "fedavg"
    selection: str = "all"
    dataset: str = "mnist"          # "mnist" | "fashion_mnist" (same shape, swap-able)
    iid: bool = True
    dropout_rate: float = 0.0       # 0..1 — fraction of selected clients that "drop"
    num_clients: int = 8
    rounds: int = 20
    local_epochs: int = 1
    batch_size: int = 32
    client_fraction: float = 1.0
    min_clients: int = 2
    seed: int = 0

    def asdict(self):
        return asdict(self)


@dataclass
class RoundResult:
    round: int
    participants: int
    test_loss: float
    test_accuracy: float
    duration_sec: float


@dataclass
class BenchmarkResult:
    id: str
    scenario: dict
    rounds: list[dict] = field(default_factory=list)
    final_test_loss: float = 0.0
    final_test_accuracy: float = 0.0
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    status: str = "running"
    error: str | None = None

    def asdict(self):
        return asdict(self)


# --------- helpers ----------

def _partition(n_samples: int, n_clients: int, iid: bool, rng: np.random.Generator,
               labels: np.ndarray) -> list[np.ndarray]:
    idx = np.arange(n_samples)
    if iid:
        rng.shuffle(idx)
        return np.array_split(idx, n_clients)
    # non-IID: sort by label, give each client 2 contiguous shards
    order = np.argsort(labels, kind="stable")
    shards_per_client = 2
    shards = np.array_split(order, n_clients * shards_per_client)
    shard_ids = list(range(len(shards)))
    rng.shuffle(shard_ids)
    out = []
    for i in range(n_clients):
        ids = shard_ids[i * shards_per_client : (i + 1) * shards_per_client]
        out.append(np.concatenate([shards[s] for s in ids]))
    return out


def _state_dict_to_numpy(model: nn.Module) -> dict:
    return {k: v.detach().cpu().numpy().astype(np.float32) for k, v in model.state_dict().items()}


def _numpy_to_state_dict(weights: dict) -> dict:
    return {k: torch.from_numpy(np.asarray(v, dtype=np.float32)) for k, v in weights.items()}


def _evaluate(weights: dict, test_loader: DataLoader) -> tuple[float, float]:
    model = CnnMnistModule()
    model.load_state_dict(_numpy_to_state_dict(weights), strict=False)
    model.eval()
    criterion = nn.CrossEntropyLoss()
    n = 0; correct = 0; loss_sum = 0.0
    with torch.no_grad():
        for xb, yb in test_loader:
            out = model(xb)
            loss_sum += criterion(out, yb).item() * yb.size(0)
            correct += (out.argmax(1) == yb).sum().item()
            n += yb.size(0)
    return float(loss_sum / max(n, 1)), float(correct / max(n, 1))


def _local_train(weights: dict, x: np.ndarray, y: np.ndarray, epochs: int,
                 batch_size: int, seed: int) -> dict:
    torch.manual_seed(seed)
    model = CnnMnistModule()
    model.load_state_dict(_numpy_to_state_dict(weights), strict=False)
    model.train()
    opt = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    crit = nn.CrossEntropyLoss()
    n = len(x)
    for _ in range(epochs):
        order = np.random.default_rng(seed).permutation(n)
        for start in range(0, n, batch_size):
            sel = order[start : start + batch_size]
            xb = torch.from_numpy(x[sel]).float()
            yb = torch.from_numpy(y[sel]).long()
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
    return _state_dict_to_numpy(model)


# --------- runner ----------

class BenchmarkRunner:
    def __init__(self) -> None:
        # Cache one (train, test_loader) tuple per dataset name so we can run
        # back-to-back scenarios across datasets without re-downloading.
        self._cache: dict[str, tuple[np.ndarray, np.ndarray, DataLoader]] = {}
        self._train_x: np.ndarray | None = None
        self._train_y: np.ndarray | None = None
        self._test_loader: DataLoader | None = None

    def _ensure_data(self, dataset: str = "mnist"):
        if dataset not in self._cache:
            tr_x, tr_y = _idx_io.load_train(dataset)
            tx, ty = _idx_io.load_test(dataset)
            loader = DataLoader(
                TensorDataset(torch.from_numpy(tx).float(), torch.from_numpy(ty).long()),
                batch_size=512, shuffle=False, num_workers=0,
            )
            self._cache[dataset] = (tr_x, tr_y, loader)
        self._train_x, self._train_y, self._test_loader = self._cache[dataset]

    def run(self, scenario: Scenario,
            on_progress: Callable[[BenchmarkResult], None] | None = None) -> BenchmarkResult:
        self._ensure_data(scenario.dataset)
        result = BenchmarkResult(id=uuid.uuid4().hex[:8], scenario=scenario.asdict())
        try:
            rng = np.random.default_rng(scenario.seed)
            shards = _partition(len(self._train_x), scenario.num_clients,
                                scenario.iid, rng, self._train_y)

            client_ids = [f"sim-{i:02d}" for i in range(scenario.num_clients)]
            shard_map = dict(zip(client_ids, shards))

            algo = algorithms.get(scenario.algorithm)
            sel_policy = selection.get(scenario.selection)

            torch.manual_seed(scenario.seed)
            global_w = _state_dict_to_numpy(CnnMnistModule())

            for r in range(scenario.rounds):
                t0 = time.time()
                # Build fake client states so the selection policy can score them.
                states = []
                for cid in client_ids:
                    s = ClientState(client_id=cid, kind="bench", active=True)
                    # synthetic dropout risk so dropout_aware sees something useful
                    s.dropout_risk = float(rng.uniform(0, 1)) if scenario.dropout_rate > 0 else 0.0
                    states.append(s)

                picked_ids = sel_policy.select(states, r, scenario.client_fraction, scenario.min_clients)

                # apply dropout: with prob dropout_rate, the selected client fails to submit.
                drops = {cid for cid in picked_ids if rng.random() < scenario.dropout_rate}
                survivors = [cid for cid in picked_ids if cid not in drops]
                if len(survivors) < scenario.min_clients:
                    survivors = picked_ids[:scenario.min_clients]   # avoid degenerate empty round

                updates = []
                for cid in survivors:
                    idx = shard_map[cid]
                    new_w = _local_train(global_w, self._train_x[idx], self._train_y[idx],
                                         scenario.local_epochs, scenario.batch_size,
                                         seed=scenario.seed + r)
                    updates.append({
                        "client_id": cid,
                        "weights": to_jsonable(new_w),
                        "num_samples": len(idx),
                        "metrics": {},
                    })

                global_w = algo.aggregate(updates, global_w)
                test_loss, test_acc = _evaluate(global_w, self._test_loader)
                result.rounds.append(asdict(RoundResult(
                    round=r,
                    participants=len(survivors),
                    test_loss=test_loss,
                    test_accuracy=test_acc,
                    duration_sec=time.time() - t0,
                )))
                if on_progress:
                    on_progress(result)

            result.final_test_loss = result.rounds[-1]["test_loss"] if result.rounds else 0.0
            result.final_test_accuracy = result.rounds[-1]["test_accuracy"] if result.rounds else 0.0
            result.status = "completed"
        except Exception as e:
            import traceback
            result.error = f"{e}\n{traceback.format_exc()}"
            result.status = "failed"
        finally:
            result.finished_at = time.time()
        return result
