# Service readiness improvements

## Implemented in this upgrade

- Workspace names and job kinds reject whitespace-only input; job targets are normalized before production checks.
- Production approval remains disabled, including mixed-case and padded target names.
- Repeating a lab approval returns the original approved record without duplicating the approval counter or event.
- Ops state transitions and snapshots use an in-process lock for concurrent HTTP handlers.
- Audit history retains the latest 5,000 events to bound event memory.
- The container runs as UID/GID 10001 and exposes a readiness health check.
- The local Kubernetes example sets resource budgets, readiness/liveness checks, and non-root process controls.

## Run and inspect

```bash
python -m pip install -r requirements.txt
python -m pytest -q
docker build -t service-lab .
docker run --rm -p 8080:8080 service-lab
```

Open `http://localhost:8080/docs` for interactive API examples. Readiness is `/v1/readyz`; liveness is `/healthz`. Resource budgets are starter values: measure workload behavior before changing them.

## Remaining deployment boundaries

State is process-local and is lost on restart. Multiple workers do not share it. The tenant header is a lab selector rather than authentication. Job approval changes a record; it does not run a workload. These improvements do not turn the prototype into a customer production control plane.
