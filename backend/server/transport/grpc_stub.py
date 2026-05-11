from .base import Transport
from .registry import register


@register
class GrpcTransport(Transport):
    """Stub gRPC transport. Real wiring would expose a bidi streaming RPC for
    weight transfer; protobuf encoding shrinks bandwidth ~5-10× vs JSON for
    dense floats, and HTTP/2 multiplexing keeps many client streams cheap."""

    name = "grpc"

    def __init__(self, port: int = 50051) -> None:
        self.port = port
        self.started = False

    def start(self):  self.started = True
    def stop(self):   self.started = False
    def broadcast(self, topic, payload): pass

    def info(self) -> dict:
        return {"name": self.name, "port": self.port, "started": self.started}
