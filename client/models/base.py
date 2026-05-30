from abc import ABC, abstractmethod
from typing import Any


class ModelRunner(ABC):
    """Client-side trainable model. Wraps real framework (PyTorch/TFLite/...).

    Implementations are responsible for serialization to a plain dict of
    numpy/list weights, so the server stays framework-agnostic.
    """

    name: str = "base"

    @abstractmethod
    def get_weights(self) -> dict[str, Any]: ...

    @abstractmethod
    def set_weights(self, weights: dict[str, Any]) -> None: ...

    @abstractmethod
    def train(self, data, epochs: int = 1) -> dict[str, Any]:
        """Run local training and return metrics dict."""

    @abstractmethod
    def evaluate(self, data) -> dict[str, Any]:
        """Return metrics dict (loss, accuracy, ...)."""
