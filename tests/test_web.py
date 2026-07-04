import pytest

fastapi = pytest.importorskip("fastapi", reason="web extra not installed")
from fastapi.testclient import TestClient  # noqa: E402

from moon_media_lab.web.server import create_app  # noqa: E402


@pytest.fixture()
def client(lab_home):
    return TestClient(create_app())


def test_status(client):
    payload = client.get("/api/status").json()
    assert "version" in payload
    assert isinstance(payload["tasks"], list)


def test_jobs_empty(client):
    assert client.get("/api/jobs").json() == {"jobs": []}


def test_submit_requires_source(client):
    assert client.post("/api/jobs", json={}).status_code == 422


def test_job_not_found(client):
    assert client.get("/api/jobs/nope").status_code == 404


def test_artifact_whitelist(client, lab_home):
    job = lab_home / "jobs" / "transcribe-x"
    job.mkdir(parents=True)
    (job / "secret.txt").write_text("no", encoding="utf-8")
    assert client.get("/api/jobs/transcribe-x/file/secret.txt").status_code == 403


def test_index_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Moon Media Lab" in response.text
