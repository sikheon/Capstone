import platform
import socket


APP_VERSION = "0.1.0"


def _detect_hw() -> str | None:
    """Best-effort hardware model detection on Linux ARM SBCs."""
    try:
        with open("/proc/device-tree/model", "rb") as f:
            return f.read().decode("utf-8", errors="ignore").strip("\x00").strip() or None
    except FileNotFoundError:
        return None
    except Exception:
        return None


def collect(kind: str) -> dict:
    return {
        "kind": kind,
        "os": platform.system(),
        "arch": platform.machine(),
        "hostname": socket.gethostname(),
        "model_hw": _detect_hw() or platform.platform(terse=True),
        "app_version": APP_VERSION,
        "metadata": {
            "python": platform.python_version(),
            "release": platform.release(),
        },
    }
