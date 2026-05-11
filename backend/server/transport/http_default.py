from .base import Transport
from .registry import register


@register
class HttpTransport(Transport):
    """Default: the FastAPI REST routes do everything (JSON over HTTP). No
    separate process / broker needed. Easiest to deploy, but bulky for large
    model weights since JSON is verbose."""

    name = "http"

    def start(self): pass
    def stop(self):  pass
    def broadcast(self, topic, payload):
        # delivered via the existing EventBus / WS; here is a no-op
        pass
