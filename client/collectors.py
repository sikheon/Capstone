"""Edge-side data collector slot — the Gboard pattern.

Mirror of android/.../data/DataCollector.kt. Concrete collectors observe a
real signal source (e.g. a sensor stream, a camera, a log file) and emit
self-labeled samples; the FL loop stays unchanged.

We ship two placeholders so the rest of the pipeline is exercisable today;
real collectors slot in by registering with `register()`.
"""

from __future__ import annotations
from typing import Callable, Iterable, Iterator
import numpy as np


class DataCollector:
    """Interface. Any new collector implements .count() and .drain()."""
    name: str = "abstract"
    min_batch: int = 32
    description: str = ""

    def count(self) -> int:
        raise NotImplementedError

    def drain(self, batch_size: int = 32) -> Iterator[tuple[np.ndarray, np.ndarray]] | None:
        """Return an iterator of (x, y) batches, OR None if not enough samples
        have been collected yet (the FL loop should skip training)."""
        raise NotImplementedError

    def reset(self) -> None:
        pass


class NoopCollector(DataCollector):
    """No live collection — train on the static DatasetLoader instead."""
    name = "none"
    description = "정적 데이터셋 사용 (수집 안함)"
    def count(self) -> int: return 0
    def drain(self, batch_size: int = 32): return None


class MockCollector(DataCollector):
    """Demo collector. Synthesises one mock 28x28 sample every count() call
    until min_batch is reached, so the UI's '0/32 → 32/32' progress animates
    even with no real input source attached. Not a real classifier."""
    name = "mock"
    description = "데모용 가짜 수집기 (자동 누적)"
    min_batch = 32

    def __init__(self) -> None:
        self._x: list[np.ndarray] = []
        self._y: list[int] = []
        self._rng = np.random.default_rng(42)

    def _tick(self) -> None:
        while len(self._x) < self.min_batch:
            self._x.append(self._rng.random((1, 28, 28), dtype=np.float32))
            self._y.append(int(self._rng.integers(0, 10)))

    def count(self) -> int:
        self._tick(); return len(self._x)

    def drain(self, batch_size: int = 32):
        self._tick()
        if len(self._x) < self.min_batch: return None
        xs = np.stack(self._x); ys = np.asarray(self._y, dtype=np.int64)
        self._x.clear(); self._y.clear()
        def _iter():
            for s in range(0, len(xs), batch_size):
                yield xs[s:s+batch_size], ys[s:s+batch_size]
        return _iter()

    def reset(self) -> None: self._x.clear(); self._y.clear()


_REGISTRY: dict[str, Callable[[], DataCollector]] = {
    "none": NoopCollector,
    "mock": MockCollector,
    # Future: register("sensor_log", SensorLogCollector)
    # Future: register("camera",     CameraCaptureCollector)
}


def register(name: str, factory: Callable[[], DataCollector]) -> None:
    _REGISTRY[name] = factory


def get(name: str) -> DataCollector:
    return _REGISTRY.get(name, _REGISTRY["none"])()


def available() -> list[str]:
    return sorted(_REGISTRY)
