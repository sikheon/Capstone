from abc import ABC, abstractmethod
from ..core.client_manager import ClientState


class DropoutPredictor(ABC):
    """Maps a client state to a (risk, reasons) tuple."""

    name: str = "base"

    @abstractmethod
    def predict(self, state: ClientState) -> tuple[float, list[str]]:
        """Return (risk in 0..1, list of human-readable reasons)."""
