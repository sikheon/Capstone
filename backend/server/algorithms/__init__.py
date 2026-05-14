from . import fedavg  # noqa: F401  (registers default algorithm)
from .registry import get, available, register
from .base import FLAlgorithm

__all__ = ["FLAlgorithm", "get", "available", "register"]
