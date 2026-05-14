import hashlib
import numpy as np
from .base import DatasetSpec
from .registry import register
from . import _idx_io


@register
class Mnist(DatasetSpec):
    """MNIST dataset spec. Actual tensors are loaded by the client; the server
    only decides how the index space is split across clients and can push a
    small training sample to mobile/edge clients via .sample()."""

    name = "mnist"
    num_classes = 10
    input_shape = (1, 28, 28)
    total_samples = 60000  # train set size

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
        """Return a deterministic per-client sample of the MNIST training set,
        formatted for direct on-device use:

        {
          "name": "mnist", "n": <int>, "h": 28, "w": 28, "num_classes": 10,
          "x": [[float * 784], ...],   # row-major, [0..1]
          "y": [int, ...],
        }

        Stable selection: a given client_id always gets the same indices,
        regardless of how many other clients are connected — so the test data
        feels "assigned to this device"."""
        x, y = _idx_io.load_train("mnist")
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
            "x": x[sel].reshape(n, 28 * 28).tolist(),
            "y": y[sel].astype(int).tolist(),
        }
