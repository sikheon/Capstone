"""Fashion-MNIST DatasetSpec — same shape as MNIST (28x28 grayscale, 10
classes) so the CnnMnist model can be reused as-is. Demonstrates the
plug-in story: swap dataset at runtime, no model/client code changes."""

import hashlib
import numpy as np

from .base import DatasetSpec
from .registry import register
from . import _idx_io


_CLASS_NAMES = (
    "T-shirt/top", "Trouser", "Pullover", "Dress", "Coat",
    "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot",
)


@register
class FashionMnist(DatasetSpec):
    name = "fashion_mnist"
    num_classes = 10
    input_shape = (1, 28, 28)
    total_samples = 60000
    class_names = _CLASS_NAMES

    def partition(self, client_ids, iid=True, seed=0):
        rng = np.random.default_rng(seed)
        n = self.total_samples
        idx = np.arange(n)
        if iid:
            rng.shuffle(idx)
            chunks = np.array_split(idx, len(client_ids))
        else:
            shards_per_client = 2
            num_shards = len(client_ids) * shards_per_client
            shard_size = n // num_shards
            shard_ids = list(range(num_shards))
            rng.shuffle(shard_ids)
            chunks = []
            for i in range(len(client_ids)):
                picked = shard_ids[i * shards_per_client : (i + 1) * shards_per_client]
                buf = np.concatenate([idx[s * shard_size : (s + 1) * shard_size] for s in picked])
                chunks.append(buf)
        return {cid: c.tolist() for cid, c in zip(client_ids, chunks)}

    def sample(self, n: int, client_id: str | None = None) -> dict:
        x, y = _idx_io.load_train("fashion_mnist")
        seed_src = (client_id or "anon").encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(seed_src).digest()[:4], "big")
        rng = np.random.default_rng(seed)
        n = max(1, min(n, len(x)))
        sel = rng.choice(len(x), size=n, replace=False)
        return {
            "name": self.name,
            "n": int(n),
            "h": 28, "w": 28,
            "num_classes": self.num_classes,
            "class_names": list(_CLASS_NAMES),
            "x": x[sel].reshape(n, 28 * 28).tolist(),
            "y": y[sel].astype(int).tolist(),
        }
