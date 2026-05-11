import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ClientState:
    client_id: str
    kind: str = "unknown"            # "android" | "edge" | "cli" | "sim"
    # device identity ↓ sent on register
    os: str | None = None            # "Linux" | "Android" | ...
    arch: str | None = None          # "aarch64" | "x86_64" | ...
    hostname: str | None = None
    model_hw: str | None = None      # "Raspberry Pi 5" | "Jetson Nano" | ...
    app_version: str | None = None
    registered_at: float | None = None
    # runtime telemetry ↓ updated on heartbeat
    last_seen: float = field(default_factory=time.time)
    battery: float | None = None     # 0.0 ~ 1.0
    charging: bool | None = None
    network: str | None = None       # "wifi" | "cell" | "ethernet" | "none"
    cpu_load: float | None = None
    dropout_risk: float = 0.0
    active: bool = True
    metadata: dict = field(default_factory=dict)


class ClientManager:
    """Thread-safe registry of connected FL clients."""

    def __init__(self) -> None:
        self._clients: dict[str, ClientState] = {}
        self._lock = Lock()

    def upsert(self, client_id: str, **fields) -> ClientState:
        with self._lock:
            state = self._clients.get(client_id) or ClientState(client_id=client_id)
            for k, v in fields.items():
                if hasattr(state, k):
                    setattr(state, k, v)
                else:
                    state.metadata[k] = v
            state.last_seen = time.time()
            self._clients[client_id] = state
            return state

    def get(self, client_id: str) -> ClientState | None:
        with self._lock:
            return self._clients.get(client_id)

    def all(self) -> list[ClientState]:
        with self._lock:
            return list(self._clients.values())

    def available(self, max_age_sec: int = 30) -> list[str]:
        cutoff = time.time() - max_age_sec
        with self._lock:
            return [c.client_id for c in self._clients.values()
                    if c.active and c.last_seen >= cutoff]

    def deactivate(self, client_id: str) -> None:
        with self._lock:
            if client_id in self._clients:
                self._clients[client_id].active = False
