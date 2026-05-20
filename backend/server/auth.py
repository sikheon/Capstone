"""Minimal in-memory auth for the capstone.

- Admins: username/password → bearer token. Default admin is `admin`/`admin`
  (override via FL_ADMIN_USER / FL_ADMIN_PASS env vars in production).
- Clients: server-issued (client_id, secret). Clients call POST /api/provision
  once, store the secret, and pass it on every subsequent request.
- Banned client_ids can never re-register.
"""

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class AuthManager:
    admin_user: str = field(default_factory=lambda: os.environ.get("FL_ADMIN_USER", "admin"))
    _admin_hash: str = field(default_factory=lambda: _hash(os.environ.get("FL_ADMIN_PASS", "admin")))
    _admin_tokens: dict[str, float] = field(default_factory=dict)   # token -> issued_at
    _clients: dict[str, str] = field(default_factory=dict)          # client_id -> secret_hash
    _banned: set[str] = field(default_factory=set)
    token_ttl_sec: int = 60 * 60 * 8

    # ---- admin ----
    def admin_login(self, username: str, password: str) -> str | None:
        if username != self.admin_user or _hash(password) != self._admin_hash:
            return None
        token = secrets.token_urlsafe(32)
        self._admin_tokens[token] = time.time()
        return token

    def admin_logout(self, token: str) -> None:
        self._admin_tokens.pop(token, None)

    def verify_admin(self, token: str | None) -> bool:
        if not token:
            return False
        issued = self._admin_tokens.get(token)
        if issued is None:
            return False
        if time.time() - issued > self.token_ttl_sec:
            self._admin_tokens.pop(token, None)
            return False
        return True

    # ---- clients ----
    def provision_client(self, suggested_id: str | None = None) -> tuple[str, str]:
        if suggested_id and suggested_id in self._banned:
            raise PermissionError("banned")
        cid = suggested_id or f"cli-{secrets.token_hex(4)}"
        # if the suggested_id is already in use, fall back to a random one
        if cid in self._clients:
            cid = f"cli-{secrets.token_hex(4)}"
        secret = secrets.token_urlsafe(24)
        self._clients[cid] = _hash(secret)
        return cid, secret

    def verify_client(self, client_id: str | None, secret: str | None) -> bool:
        if not client_id or not secret:
            return False
        if client_id in self._banned:
            return False
        h = self._clients.get(client_id)
        return h is not None and _hash(secret) == h

    def revoke_client(self, client_id: str) -> None:
        self._clients.pop(client_id, None)

    def ban_client(self, client_id: str) -> None:
        self._banned.add(client_id)
        self.revoke_client(client_id)

    def unban_client(self, client_id: str) -> None:
        self._banned.discard(client_id)

    def is_banned(self, client_id: str) -> bool:
        return client_id in self._banned

    def banned_list(self) -> list[str]:
        return sorted(self._banned)


auth = AuthManager()
