"""Fashion-MNIST client loader. Same shape as MNIST (28x28 grayscale, 10
classes) so it slots into the existing CnnMnist model unchanged."""

import os
import numpy as np
import torch
from torchvision import datasets, transforms

from .base import DatasetLoader
from .registry import register


_CACHE_DIR = os.environ.get("FL_DATA_DIR", os.path.expanduser("~/.flclient/data"))


@register
class FashionMnistLoader(DatasetLoader):
    name = "fashion_mnist"

    def __init__(self) -> None:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        # Fashion-MNIST has its own mean/std; values from torchvision docs.
        tf = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.2860,), (0.3530,)),
        ])
        train = datasets.FashionMNIST(_CACHE_DIR, train=True, download=True, transform=tf)
        self._x = torch.stack([train[i][0] for i in range(len(train))]).numpy().astype(np.float32)
        self._y = np.asarray([train[i][1] for i in range(len(train))], dtype=np.int64)

    def size(self) -> int:
        return len(self._x)

    def load(self, indices=None, batch_size=32):
        idx = np.arange(self.size()) if indices is None else np.asarray(indices)
        rng = np.random.default_rng()
        rng.shuffle(idx)
        for start in range(0, len(idx), batch_size):
            sl = idx[start : start + batch_size]
            yield self._x[sl], self._y[sl]
