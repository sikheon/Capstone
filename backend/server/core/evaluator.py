"""Server-side evaluator for the *global* model.

Per-round client metrics (in orchestrator.metric_history) are training-set
averages weighted by the clients that happened to participate — they don't
tell you how the aggregated global model actually performs on held-out data.
This module fixes that: build the model fresh, load current global_weights,
run a held-out test pass."""

import time
import threading

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ..models.cnn_mnist import CnnMnistModule
from ..datasets import _idx_io


# Test sets we know how to load held-out data for. cnn_mnist works as-is on
# both since both are 28x28 grayscale 10-class.
_KNOWN_TESTS = {"mnist", "fashion_mnist"}


class GlobalEvaluator:
    """Lazy IDX-format test-set evaluator. Loads ~5 MB per dataset on first
    call, then caches in memory. Thread-safe across datasets."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaders: dict[str, DataLoader] = {}
        self.last: dict | None = None
        self.history: list[dict] = []

    def _ensure_test(self, dataset: str) -> DataLoader:
        if dataset not in self._loaders:
            x, y = _idx_io.load_test(dataset)
            self._loaders[dataset] = DataLoader(
                TensorDataset(torch.from_numpy(x).float(), torch.from_numpy(y).long()),
                batch_size=256, shuffle=False, num_workers=0,
            )
        return self._loaders[dataset]

    def evaluate(self, weights: dict, model_name: str = "cnn_mnist",
                 round_num: int | None = None, dataset: str = "mnist") -> dict:
        """Build the model fresh, load weights, eval on the dataset's held-out
        test set. Both MNIST and Fashion-MNIST use CnnMnistModule (same shape)."""
        with self._lock:
            if model_name != "cnn_mnist":
                return {"error": f"evaluator only knows cnn_mnist (got {model_name})"}
            if dataset not in _KNOWN_TESTS:
                return {"error": f"no held-out test set wired for dataset={dataset}"}

            loader = self._ensure_test(dataset)
            model = CnnMnistModule()
            sd = {k: torch.tensor(np.asarray(v), dtype=torch.float32) for k, v in weights.items()}
            model.load_state_dict(sd, strict=False)
            model.eval()

            criterion = nn.CrossEntropyLoss()
            n = 0
            correct = 0
            loss_sum = 0.0
            t0 = time.time()
            with torch.no_grad():
                for xb, yb in loader:
                    out = model(xb)
                    loss_sum += criterion(out, yb).item() * yb.size(0)
                    correct += (out.argmax(1) == yb).sum().item()
                    n += yb.size(0)
            result = {
                "round": round_num,
                "model": model_name,
                "dataset": dataset,
                "test_loss": float(loss_sum / max(n, 1)),
                "test_accuracy": float(correct / max(n, 1)),
                "test_samples": int(n),
                "eval_duration_sec": time.time() - t0,
                "evaluated_at": time.time(),
            }
            self.last = result
            self.history.append(result)
            return result
