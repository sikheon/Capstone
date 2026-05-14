"""Tiny pure-numpy MNIST loader. Downloads the IDX files on first call into a
cache dir, parses them, and exposes them as (x, y) numpy arrays. No
torchvision dependency on the server."""

import gzip
import io
import os
import urllib.request
from pathlib import Path

import numpy as np

CACHE_DIR = Path(os.environ.get("FL_SERVER_DATA_DIR", Path.home() / ".flserver" / "mnist"))
MIRROR = "https://storage.googleapis.com/cvdf-datasets/mnist"


def _download(name: str) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / name
    if not path.exists():
        url = f"{MIRROR}/{name}"
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        path.write_bytes(data)
    return path.read_bytes()


def _decode_images(raw: bytes) -> np.ndarray:
    with gzip.open(io.BytesIO(raw)) as f:
        magic = int.from_bytes(f.read(4), "big")
        assert magic == 2051, f"bad image magic {magic}"
        n = int.from_bytes(f.read(4), "big")
        h = int.from_bytes(f.read(4), "big")
        w = int.from_bytes(f.read(4), "big")
        buf = np.frombuffer(f.read(), dtype=np.uint8)
        return buf.reshape(n, 1, h, w).astype(np.float32) / 255.0


def _decode_labels(raw: bytes) -> np.ndarray:
    with gzip.open(io.BytesIO(raw)) as f:
        magic = int.from_bytes(f.read(4), "big")
        assert magic == 2049, f"bad label magic {magic}"
        _ = int.from_bytes(f.read(4), "big")
        return np.frombuffer(f.read(), dtype=np.uint8).astype(np.int64)


_TRAIN_X: np.ndarray | None = None
_TRAIN_Y: np.ndarray | None = None
_TEST_X: np.ndarray | None = None
_TEST_Y: np.ndarray | None = None


def load_train() -> tuple[np.ndarray, np.ndarray]:
    global _TRAIN_X, _TRAIN_Y
    if _TRAIN_X is None:
        _TRAIN_X = _decode_images(_download("train-images-idx3-ubyte.gz"))
        _TRAIN_Y = _decode_labels(_download("train-labels-idx1-ubyte.gz"))
    return _TRAIN_X, _TRAIN_Y


def load_test() -> tuple[np.ndarray, np.ndarray]:
    global _TEST_X, _TEST_Y
    if _TEST_X is None:
        _TEST_X = _decode_images(_download("t10k-images-idx3-ubyte.gz"))
        _TEST_Y = _decode_labels(_download("t10k-labels-idx1-ubyte.gz"))
    return _TEST_X, _TEST_Y
