from abc import ABC, abstractmethod
from typing import Iterable


class DatasetLoader(ABC):
    """Client-side dataset loader. Owns the actual tensors / files."""

    name: str = "base"

    @abstractmethod
    def load(self, indices: list[int] | None = None, batch_size: int = 32) -> Iterable:
        """Return iterable of (x, y) batches."""

    @abstractmethod
    def size(self) -> int: ...
