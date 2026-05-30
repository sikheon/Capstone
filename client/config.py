import os
from dataclasses import dataclass


@dataclass
class ClientConfig:
    # Central server endpoint — overridable so the server can move anytime.
    server_url: str = os.environ.get("FL_SERVER_URL", "http://localhost:8000")
    client_id: str = os.environ.get("FL_CLIENT_ID", "edge-0")
    kind: str = os.environ.get("FL_CLIENT_KIND", "edge")  # edge | sim

    algorithm: str = os.environ.get("FL_ALGO", "fedavg")
    model: str = os.environ.get("FL_MODEL", "cnn_mnist")
    dataset: str = os.environ.get("FL_DATASET", "mnist")

    heartbeat_sec: int = int(os.environ.get("FL_HEARTBEAT_SEC", "5"))
    local_epochs: int = int(os.environ.get("FL_LOCAL_EPOCHS", "1"))

    # Gboard-pattern background data collector. "none" → use the static
    # `dataset` loader; other values come from collectors.register().
    collector: str = os.environ.get("FL_COLLECTOR", "none")


config = ClientConfig()
