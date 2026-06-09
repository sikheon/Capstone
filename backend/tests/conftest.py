import os
import sys
import pytest
from fastapi.testclient import TestClient

# make `server.*` importable when running `pytest backend/`
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


@pytest.fixture()
def client():
    # fresh module state per test (singletons in auth/orchestrator).
    for k in list(sys.modules):
        if k.startswith("server"):
            del sys.modules[k]
    from server.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    r = client.post("/api/admin/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture()
def provisioned(client):
    r = client.post("/api/provision", json={"suggested_id": "test-client"})
    assert r.status_code == 200
    return r.json()
