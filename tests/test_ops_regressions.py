import pytest
from fastapi.testclient import TestClient
from pdfqa.main import app

client = TestClient(app)


@pytest.mark.parametrize("target", ["PROD", " Production ", "pRoD"])
def test_production_target_is_canonical_and_refused(target):
    headers = {"X-Tenant-Id": "upgrade-prod"}
    ws = client.post("/v1/workspaces", json={"name": "test"}, headers=headers).json()
    job = client.post(f"/v1/workspaces/{ws['id']}/jobs", json={"kind": "evaluate", "target": target}, headers=headers).json()
    assert job["status"] == "pending_approval"
    assert job["target"] in {"prod", "production"}
    assert client.post(f"/v1/jobs/{job['id']}/approve", headers=headers).status_code == 403


def test_duplicate_approval_is_idempotent():
    headers = {"X-Tenant-Id": "upgrade-repeat"}
    ws = client.post("/v1/workspaces", json={"name": "test"}, headers=headers).json()
    job = client.post(f"/v1/workspaces/{ws['id']}/jobs", json={"kind": "evaluate"}, headers=headers).json()
    first = client.post(f"/v1/jobs/{job['id']}/approve", headers=headers).json()
    count = client.get("/v1/metrics").json()["approvals_granted"]
    second = client.post(f"/v1/jobs/{job['id']}/approve", headers=headers).json()
    assert second["approved_at"] == first["approved_at"]
    assert client.get("/v1/metrics").json()["approvals_granted"] == count


def test_whitespace_workspace_name_is_rejected():
    assert client.post("/v1/workspaces", json={"name": "   "}).status_code == 422


def test_blank_job_target_is_rejected():
    ws = client.post("/v1/workspaces", json={"name": "test"}).json()
    assert client.post(f"/v1/workspaces/{ws['id']}/jobs", json={"kind": "evaluate", "target": " "}).status_code == 422


def test_other_tenant_cannot_approve_job():
    headers = {"X-Tenant-Id": "upgrade-owner"}
    ws = client.post("/v1/workspaces", json={"name": "test"}, headers=headers).json()
    job = client.post(f"/v1/workspaces/{ws['id']}/jobs", json={"kind": "evaluate"}, headers=headers).json()
    assert client.post(f"/v1/jobs/{job['id']}/approve", headers={"X-Tenant-Id": "other"}).status_code == 404
