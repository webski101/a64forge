from fastapi.testclient import TestClient

from a64forge.api.main import app


def test_health_and_system_endpoints(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("A64FORGE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("A64FORGE_DEV_MODE", "true")
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["verified_arm64"] is False
    system = client.get("/system")
    assert system.status_code == 200
    assert system.json()["dev_mode"] is True

