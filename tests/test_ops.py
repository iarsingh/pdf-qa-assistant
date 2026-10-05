
from fastapi.testclient import TestClient
from pdfqa.main import app

client = TestClient(app)


def test_readyz():
    r = client.get("/v1/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_workspace_and_job_happy_path():
    ws = client.post("/v1/workspaces", json={"name": "lab-a", "environment": "lab"}, headers={"X-Tenant-Id": "acme"}).json()
    assert ws["id"]
    job = client.post(
        f"/v1/workspaces/{ws['id']}/jobs",
        json={"kind": "evaluate", "payload": {"sample": True}, "target": "lab"},
        headers={"X-Tenant-Id": "acme"},
    )
    assert job.status_code == 201
    body = job.json()
    assert body["status"] in {"queued", "pending_approval"}
    got = client.get(f"/v1/jobs/{body['id']}", headers={"X-Tenant-Id": "acme"})
    assert got.status_code == 200


def test_tenant_isolation():
    ws = client.post("/v1/workspaces", json={"name": "secret"}, headers={"X-Tenant-Id": "t1"}).json()
    listed = client.get("/v1/workspaces", headers={"X-Tenant-Id": "t2"}).json()
    assert all(item["id"] != ws["id"] for item in listed["items"])


def test_missing_workspace_404():
    r = client.post(
        "/v1/workspaces/does-not-exist/jobs",
        json={"kind": "x", "payload": {}, "target": "lab"},
        headers={"X-Tenant-Id": "acme"},
    )
    assert r.status_code == 404


def test_prod_apply_refused():
    ws = client.post("/v1/workspaces", json={"name": "prod-ws"}, headers={"X-Tenant-Id": "acme"}).json()
    job = client.post(
        f"/v1/workspaces/{ws['id']}/jobs",
        json={"kind": "apply", "payload": {}, "target": "prod"},
        headers={"X-Tenant-Id": "acme"},
    ).json()
    assert job["status"] == "pending_approval"
    refused = client.post(f"/v1/jobs/{job['id']}/approve", headers={"X-Tenant-Id": "acme"})
    assert refused.status_code == 403


def test_lab_approve_ok():
    ws = client.post("/v1/workspaces", json={"name": "ok"}, headers={"X-Tenant-Id": "acme"}).json()
    job = client.post(
        f"/v1/workspaces/{ws['id']}/jobs",
        json={"kind": "run", "payload": {}, "target": "lab"},
        headers={"X-Tenant-Id": "acme"},
    ).json()
    ok = client.post(f"/v1/jobs/{job['id']}/approve", headers={"X-Tenant-Id": "acme"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "approved"


def test_audit_and_metrics():
    metrics = client.get("/v1/metrics").json()
    assert "jobs_created" in metrics
    audit = client.get("/v1/audit", headers={"X-Tenant-Id": "acme"}).json()
    assert "items" in audit


def test_job_not_found():
    assert client.get("/v1/jobs/missing", headers={"X-Tenant-Id": "acme"}).status_code == 404
