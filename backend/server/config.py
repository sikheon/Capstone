import os
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000

    algorithm: str = "fedavg"
    model: str = "cnn_mnist"
    dataset: str = "mnist"
    selection: str = "all"
    transport: str = "http"     # http | mqtt | grpc (see backend/server/transport/)

    mode: str = "sync"          # sync = round-based; async = continuous aggregation
    # Gboard-style always-on. Set FL_AUTO_START=async (or sync) so the orchestrator
    # starts on boot — no admin click needed. Empty / unset = stay stopped.
    auto_start: str = field(default_factory=lambda: os.environ.get("FL_AUTO_START", ""))

    total_rounds: int = 1_000_000  # effectively unbounded for always-on
    min_clients_per_round: int = 2
    client_fraction: float = 1.0
    round_timeout_sec: int = 120
    local_epochs: int = 1

    # async-mode knobs
    async_blend: float = 0.1            # global ← (1-blend)*global + blend*client_update
    async_min_interval_sec: float = 0.5 # rate-limit per-client contributions

    dropout_threshold: float = 0.5
    auto_dropout_control: bool = True


config = ServerConfig()
