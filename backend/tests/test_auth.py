def test_admin_login_required_for_param_patch(client):
    r = client.patch("/api/params", json={"local_epochs": 3})
    assert r.status_code == 401


def test_admin_login_and_patch(client, admin_token):
    r = client.patch("/api/params", json={"local_epochs": 5},
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["local_epochs"] == 5


def test_provision_then_heartbeat(client, provisioned):
    cid = provisioned["client_id"]
    secret = provisioned["client_secret"]
    r = client.post("/api/heartbeat",
                    json={"client_id": cid, "kind": "edge"},
                    headers={"X-Client-Id": cid, "X-Client-Secret": secret})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "orchestrator_state" in body
    assert "mode" in body


def test_heartbeat_without_credentials_rejected(client):
    r = client.post("/api/heartbeat", json={"client_id": "x", "kind": "edge"})
    assert r.status_code == 401


def test_ban_blocks_reprovisioning(client, admin_token, provisioned):
    cid = provisioned["client_id"]
    r = client.post(f"/api/admin/ban/{cid}",
                    headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    r = client.post("/api/provision", json={"suggested_id": cid})
    assert r.status_code == 403
