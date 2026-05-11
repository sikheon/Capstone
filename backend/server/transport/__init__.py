"""Transport plug-in slot.

The active deployment uses plain HTTP+WS (see api/), but the FL data plane
(model-weight transfer) is what really benefits from something denser/binary.
Subclass `Transport`, register, and switch via config.transport — same pattern
as the rest of the system.
"""

from . import http_default, mqtt_stub, grpc_stub  # noqa: F401
from .registry import get, available, register
from .base import Transport

__all__ = ["Transport", "get", "available", "register"]
