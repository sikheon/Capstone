from .base import SelectionPolicy
from .registry import register


@register
class DropoutAware(SelectionPolicy):
    """Prefer low-risk clients. The whole point of the capstone — pick the ones
    least likely to drop mid-round."""

    name = "dropout_aware"

    def select(self, candidates, round_num, fraction, min_clients):
        if not candidates:
            return []
        sorted_by_risk = sorted(candidates, key=lambda c: c.dropout_risk)
        k = max(min_clients, int(len(candidates) * fraction))
        k = min(k, len(candidates))
        return [c.client_id for c in sorted_by_risk[:k]]
