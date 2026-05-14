import random
from .base import SelectionPolicy
from .registry import register


@register
class RandomSubset(SelectionPolicy):
    """Uniform random sample of size max(min_clients, fraction * |pool|)."""

    name = "random"

    def select(self, candidates, round_num, fraction, min_clients):
        if not candidates:
            return []
        rng = random.Random(round_num)
        k = max(min_clients, int(len(candidates) * fraction))
        k = min(k, len(candidates))
        return [c.client_id for c in rng.sample(candidates, k)]
