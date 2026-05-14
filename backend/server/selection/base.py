from abc import ABC, abstractmethod
from ..core.client_manager import ClientState


class SelectionPolicy(ABC):
    """Decides which connected clients participate in the next round."""

    name: str = "base"

    @abstractmethod
    def select(
        self,
        candidates: list[ClientState],
        round_num: int,
        fraction: float,
        min_clients: int,
    ) -> list[str]:
        """Return list of client_ids selected for the round."""
