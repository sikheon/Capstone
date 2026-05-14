from abc import ABC, abstractmethod
from typing import Any


class ModelSpec(ABC):
    """Framework-agnostic model spec. Wraps a real model (PyTorch, TF, ...).

    The server only needs weight get/set and a parameter shape map for init.
    The training logic lives on the client.
    """

    name: str = "base"
    input_shape: tuple = ()
    num_classes: int = 0

    @abstractmethod
    def initial_weights(self) -> dict[str, Any]:
        """Return initial parameter dict (numpy arrays keyed by layer name)."""

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input_shape": list(self.input_shape),
            "num_classes": self.num_classes,
        }
