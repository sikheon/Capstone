"""Generic IDX dataset loader. Both MNIST and Fashion-MNIST ship as the same
IDX file format (Yann LeCun's), so we abstract the mirror + filename layout."""

import gzip
import io
import os
import urllib.request
from pathlib import Path

import numpy as np


_SPECS = {
    "mnist": {
        "mirror": "https://storage.googleapis.com/cvdf-datasets/mnist",
        "train_x": "train-images-idx3-ubyte.gz",
        "train_y": "train-labels-idx1-ubyte.gz",
        "test_x":  "t10k-images-idx3-ubyte.gz",
        "test_y":  "t10k-labels-idx1-ubyte.gz",
    },
    "fashion_mnist": {
        "mirror": "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com",
        "train_x": "train-images-idx3-ubyte.gz",
        "train_y": "train-labels-idx1-ubyte.gz",
        "test_x":  "t10k-images-idx3-ubyte.gz",
        "test_y":  "t10k-labels-idx1-ubyte.gz",
    },
}


def _cache_dir(dataset: str) -> Path:
    base = Path(os.environ.get("FL_SERVER_DATA_DIR", Path.home() / ".flserver"))
    p = base / dataset
    p.mkdir(parents=True, exist_ok=True)
    return p


def _download(dataset: str, name: str) -> bytes:
    spec = _SPECS[dataset]
    path = _cache_dir(dataset) / name
    if not path.exists():
        url = f"{spec['mirror']}/{name}"
        with urllib.request.urlopen(url, timeout=120) as r:
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


_TRAIN: dict[str, tuple[np.ndarray, np.ndarray]] = {}
_TEST:  dict[str, tuple[np.ndarray, np.ndarray]] = {}


def load_train(dataset: str = "mnist") -> tuple[np.ndarray, np.ndarray]:
    if dataset not in _TRAIN:
        spec = _SPECS[dataset]
        _TRAIN[dataset] = (
            _decode_images(_download(dataset, spec["train_x"])),
            _decode_labels(_download(dataset, spec["train_y"])),
        )
    return _TRAIN[dataset]


def load_test(dataset: str = "mnist") -> tuple[np.ndarray, np.ndarray]:
    if dataset not in _TEST:
        spec = _SPECS[dataset]
        _TEST[dataset] = (
            _decode_images(_download(dataset, spec["test_x"])),
            _decode_labels(_download(dataset, spec["test_y"])),
        )
    return _TEST[dataset]
