from .base import Transport
from .registry import register


@register
class MqttTransport(Transport):
    """Stub MQTT transport. Real wiring would use paho-mqtt against an external
    broker (e.g. Mosquitto, EMQX). MQTT fits async FL well — clients subscribe
    to `fl/global` for new weights and publish to `fl/updates/<client_id>` when
    they finish local training, all over a persistent TCP connection that
    survives flaky cell networks much better than HTTP request cycles."""

    name = "mqtt"

    def __init__(self, host: str = "localhost", port: int = 1883) -> None:
        self.host = host
        self.port = port
        self.started = False

    def start(self):
        # placeholder: would establish broker connection here
        self.started = True

    def stop(self):
        self.started = False

    def broadcast(self, topic, payload):
        # placeholder: would publish via paho client
        pass

    def info(self) -> dict:
        return {"name": self.name, "host": self.host, "port": self.port, "started": self.started}
