from . import mnist          # noqa: F401  (registers default dataset)
from . import fashion_mnist  # noqa: F401  (plug-in: same shape, different domain)
from .registry import get, available, register
from .base import DatasetSpec

__all__ = ["DatasetSpec", "get", "available", "register"]
