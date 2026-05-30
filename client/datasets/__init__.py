from . import mnist          # noqa: F401
from . import fashion_mnist  # noqa: F401
from .registry import get, available, register
from .base import DatasetLoader

__all__ = ["DatasetLoader", "get", "available", "register"]
