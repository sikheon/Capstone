"""Persist server-issued (client_id, client_secret) on disk so the edge
client doesn't need to re-provision on every restart."""

import json
import os
from pathlib import Path


def _path() -> Path:
    custom = os.environ.get("FL_CRED_PATH")
    return Path(custom) if custom else Path.home() / ".flclient" / "credentials.json"


def load() -> tuple[str | None, str | None]:
    p = _path()
    if not p.exists():
        return None, None
    try:
        data = json.loads(p.read_text())
        return data.get("client_id"), data.get("client_secret")
    except Exception:
        return None, None


def save(client_id: str, client_secret: str) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"client_id": client_id, "client_secret": client_secret}))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def clear() -> None:
    p = _path()
    if p.exists():
        p.unlink()
