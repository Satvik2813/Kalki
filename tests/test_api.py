"""API endpoint smoke tests. Skipped when FastAPI/httpx aren't installed
(the core does not require them)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import create_app  # noqa: E402
from backend.service import KalkiService  # noqa: E402


@pytest.fixture()
def client(settings):
    svc = KalkiService(settings=settings)
    return TestClient(create_app(svc))


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_create_start_and_inspect_run(client):
    r = client.post("/api/tasks", json={"objective": "inspect the project",
                                        "start": True})
    assert r.status_code == 200
    run_id = r.json()["id"]

    # run executes on a background thread; poll the result
    import time
    for _ in range(50):
        res = client.get(f"/api/tasks/{run_id}/result").json()
        if res.get("status") in ("completed", "failed", "blocked",
                                  "awaiting_approval"):
            break
        time.sleep(0.05)

    state = client.get(f"/api/tasks/{run_id}").json()
    assert state["id"] == run_id
    assert state["plan"] is not None

    events = client.get(f"/api/tasks/{run_id}/events").json()["events"]
    assert any(e["type"] == "PLAN_CREATED" for e in events)


def test_projects_and_memory_endpoints(client):
    assert client.get("/api/projects").status_code == 200
    assert "memories" in client.get("/api/memory").json()


def test_unknown_run_is_404(client):
    assert client.get("/api/tasks/does-not-exist").status_code == 404
