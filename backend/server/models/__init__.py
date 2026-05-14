from . import cnn_mnist  # noqa: F401  (registers default model)
from .registry import get, available, register
from .base import ModelSpec

__all__ = ["ModelSpec", "get", "available", "register"]
