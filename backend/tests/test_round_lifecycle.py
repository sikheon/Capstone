def test_status_endpoint_public(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json()["orchestrator_state"] == "stopped"


def test_start_pause_resume_stop(client, admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    assert client.get("/api/status").json()["orchestrator_state"] == "stopped"

    r = client.post("/api/admin/round/start", json={"mode": "sync"}, headers=hdr)
    assert r.status_code == 200 and r.json()["state"] in ("running", "paused")

    r = client.post("/api/admin/round/pause", headers=hdr)
    assert r.json()["state"] == "paused"

    r = client.post("/api/admin/round/resume", headers=hdr)
    assert r.json()["state"] == "running"

    r = client.post("/api/admin/round/stop", headers=hdr)
    assert r.json()["state"] == "stopped"


def test_swap_algorithm(client, admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/algorithm", json={"name": "fedavg"}, headers=hdr)
    assert r.status_code == 200
    r = client.post("/api/algorithm", json={"name": "nope"}, headers=hdr)
    assert r.status_code == 404
