import httpx
from .config import config


class FLApiClient:
    """Thin HTTP client. All requests target `config.server_url`, so swapping
    the central server only requires updating that one value (env var or flag).

    Client auth uses (X-Client-Id, X-Client-Secret) issued by /api/provision.
    """

    def __init__(self, base_url: str | None = None,
                 client_id: str | None = None, secret: str | None = None) -> None:
        self.base_url = (base_url or config.server_url).rstrip("/")
        self.client_id = client_id
        self.secret = secret
        self._http = httpx.Client(timeout=10.0)

    def _headers(self) -> dict:
        h = {}
        if self.client_id and self.secret:
            h["X-Client-Id"] = self.client_id
            h["X-Client-Secret"] = self.secret
        return h

    def provision(self, suggested_id: str | None = None) -> dict:
        r = self._http.post(f"{self.base_url}/api/provision",
                            json={"suggested_id": suggested_id})
        r.raise_for_status()
        data = r.json()
        self.client_id = data["client_id"]
        self.secret = data["client_secret"]
        return data

    def register(self, payload: dict) -> dict:
        r = self._http.post(f"{self.base_url}/api/register", json=payload, headers=self._headers())
        r.raise_for_status(); return r.json()

    def heartbeat(self, payload: dict) -> dict:
        r = self._http.post(f"{self.base_url}/api/heartbeat", json=payload, headers=self._headers())
        r.raise_for_status(); return r.json()

    def submit_update(self, payload: dict) -> dict:
        r = self._http.post(f"{self.base_url}/api/update", json=payload, headers=self._headers())
        r.raise_for_status(); return r.json()

    def status(self) -> dict:
        r = self._http.get(f"{self.base_url}/api/status")
        r.raise_for_status(); return r.json()

    def current_round(self) -> dict:
        r = self._http.get(f"{self.base_url}/api/round/current", headers=self._headers())
        r.raise_for_status(); return r.json()

    def close(self) -> None:
        self._http.close()
