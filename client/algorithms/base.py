from abc import ABC, abstractmethod
from typing import Any


class ClientAlgorithm(ABC):
    """Client-side counterpart to the server algorithm.

    Defines how the local training step transforms global weights into a delta
    (or new weights) to send back. Swap to plug in FedProx, SCAFFOLD, etc.
    """

    name: str = "base"

    @abstractmethod
    def local_train(
        self,
        model_runner,                # ModelRunner instance
        global_weights: dict[str, Any],
        data,                        # iterable of (x, y) batches
        epochs: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return (new_weights, metrics)."""
