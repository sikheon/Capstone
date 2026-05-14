from abc import ABC, abstractmethod
from typing import Any, Iterable


class DatasetSpec(ABC):
    """Pluggable dataset description.

    Server only needs metadata + a per-client partitioning policy.
    Actual data loading runs on the client side using the same `name`.
    """

    name: str = "base"
    num_classes: int = 0
    input_shape: tuple = ()

    @abstractmethod
    def partition(self, client_ids: list[str], iid: bool = True, seed: int = 0) -> dict[str, list[int]]:
        """Return {client_id: [sample_index, ...]} mapping."""

    def sample(self, n: int, client_id: str | None = None) -> dict | None:
        """Return a small sample bundle the server can push to clients for
        on-device training/eval. Optional — subclasses without local data
        just return None and the API responds 501."""
        return None

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "num_classes": self.num_classes,
            "input_shape": list(self.input_shape),
        }
