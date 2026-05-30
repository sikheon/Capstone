import platform
import time
from dataclasses import dataclass


@dataclass
class Flags:
    battery: float | None = None
    charging: bool | None = None
    network: str | None = None
    cpu_load: float | None = None


class LocalReporter:
    """Ultra-light state probe (the '초경량 플래그 추출기'). Reads only the
    minimum signals the dropout predictor needs."""

    def __init__(self) -> None:
        self._t0 = time.time()

    def collect(self) -> Flags:
        flags = Flags()
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat is not None:
                flags.battery = bat.percent / 100.0
                flags.charging = bat.power_plugged
            flags.cpu_load = psutil.cpu_percent(interval=None) / 100.0
        except Exception:
            pass

        flags.network = "wifi" if platform.system() != "Linux" else "ethernet"
        return flags
