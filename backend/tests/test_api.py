from fastapi.testclient import TestClient


def _client(settings):
    from app.api.deps import get_service
    from app.main import create_app

    get_service.cache_clear()
    return TestClient(create_app())


def test_health(settings):
    r = _client(settings).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_golden_path(settings):
    c = _client(settings)
    assert c.post("/api/demo/reset", json={"rows": 5000}).status_code == 200
    assert c.post("/api/pipeline/run", json={"set_baseline": True}).json()["status"] == "SUCCESS"
    assert c.post("/api/incidents/inject", json={"type": "filter_regression"}).status_code == 200
    assert c.post("/api/pipeline/run", json={}).json()["status"] == "SUCCESS"
    det = c.post("/api/incidents/detect").json()
    assert det["detection"]["data_health"] == "CRITICAL"
    iid = det["incident"]["id"]
    for step in ("investigate", "fix", "apply", "validate"):
        r = c.post(f"/api/incidents/{iid}/{step}")
        assert r.status_code == 200, (step, r.text)
    assert r.json()["status"] == "RESOLVED"
    state = c.get("/api/state").json()
    assert state["last_detection"]["data_health"] == "HEALTHY"
    assert "RESOLVED" in c.get(f"/api/incidents/{iid}/report").text


def test_workflow_errors_are_clean(settings):
    c = _client(settings)
    r = c.post("/api/incidents/detect")
    assert r.status_code == 409
    assert "detail" in r.json()
    assert c.post("/api/incidents/inject", json={"type": "not_a_type"}).status_code == 422
    assert c.get("/api/incidents/INC-9999").status_code == 404


def test_unexpected_errors_do_not_expose_exception_details(settings):
    from app.api.deps import get_service
    from app.main import create_app

    app = create_app()

    def fail():
        raise RuntimeError("secret diagnostic detail")

    app.dependency_overrides[get_service] = fail
    response = TestClient(app, raise_server_exceptions=False).get("/health")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
