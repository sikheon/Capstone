import numpy as np
from .base import FLAlgorithm
from .registry import register


@register
class FedAvg(FLAlgorithm):
    """Weighted average by sample count. The textbook baseline."""

    name = "fedavg"

    def aggregate(self, client_updates, global_weights):
        total = sum(u["num_samples"] for u in client_updates)
        if total == 0 or not client_updates:
            return global_weights

        new_weights: dict = {}
        for key in global_weights:
            target_shape = np.asarray(global_weights[key]).shape
            stacked = np.stack([
                np.asarray(u["weights"][key], dtype=np.float32).reshape(target_shape) *
                    (u["num_samples"] / total)
                for u in client_updates
            ])
            new_weights[key] = stacked.sum(axis=0).astype(np.float32)
        return new_weights
