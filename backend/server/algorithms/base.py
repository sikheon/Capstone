from abc import ABC, abstractmethod
from typing import Any


class FLAlgorithm(ABC):
    """Server-side federated learning aggregation algorithm.

    Subclass and register with @register to make it selectable at runtime.
    """

    name: str = "base"

    @abstractmethod
    def aggregate(
        self,
        client_updates: list[dict[str, Any]],
        global_weights: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate client updates into new global weights.

        client_updates: list of {client_id, weights, num_samples, metrics}
        """
