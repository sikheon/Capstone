from .base import SelectionPolicy
from .registry import register


@register
class AllClients(SelectionPolicy):
    """Pick everyone available — simple baseline."""

    name = "all"

    def select(self, candidates, round_num, fraction, min_clients):
        return [c.client_id for c in candidates]
