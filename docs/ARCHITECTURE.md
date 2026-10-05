# Architecture

This service keeps the original domain endpoints and adds an ops plane under `/v1`.

- Workspaces are tenant-scoped via `X-Tenant-Id`.
- Jobs targeting `prod` stay `pending_approval` and approve is refused. This is a laptop lab, not a production control plane.
- Audit events are in-memory so a restart wipes history.
- Kubernetes manifests are for local kind/minikube only; they do not apply to a customer cluster from this repo.

## Endpoints

- `GET /healthz` original
- `GET /v1/readyz`
- `POST /v1/workspaces`
- `GET /v1/workspaces`
- `POST /v1/workspaces/{{id}}/jobs`
- `GET /v1/jobs/{{id}}`
- `POST /v1/jobs/{{id}}/approve`
- `GET /v1/audit`
- `GET /v1/metrics`
