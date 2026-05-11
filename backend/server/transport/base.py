from abc import ABC, abstractmethod


class Transport(ABC):
    """Strategy for shipping model weights between coordinator and clients.

    The control plane (heartbeat / register / admin commands) stays on HTTP/WS
    regardless of which transport is active — only the bulky `update` and
    `broadcast` paths route through the chosen transport.
    """

    name: str = "base"

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def broadcast(self, topic: str, payload: bytes) -> None:
        """Push global weights / round_started events to clients."""

    def info(self) -> dict:
        return {"name": self.name}
