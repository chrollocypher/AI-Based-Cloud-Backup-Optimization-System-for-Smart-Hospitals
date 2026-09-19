import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamodb import db_memory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_data():
    db_memory.clear()
    client.post("/api/v1/records", json={
        "record_id": "EHR_10025",
        "record_type": "EHR",
        "department": "Emergency",
        "data_size_mb": 25.4,
        "access_frequency": 18
    })
    yield
    db_memory.clear()


def test_trigger_backup_for_specific_record():
    resp = client.post("/api/v1/backups", json={"record_id": "EHR_10025"})
    assert resp.status_code == 202
    jobs = resp.json()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["record_id"] == "EHR_10025"
    assert job["status"] == "COMPLETED"
    assert "s3://" in job["s3_location"]

    # Verify record status updated in DB
    rec_resp = client.get("/api/v1/records/EHR_10025")
    assert rec_resp.json()["backup_status"] == "COMPLETED"


def test_list_and_get_backup_job():
    trig = client.post("/api/v1/backups", json={"record_id": "EHR_10025"})
    job_id = trig.json()[0]["job_id"]

    list_resp = client.get("/api/v1/backups")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = client.get(f"/api/v1/backups/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["job_id"] == job_id


def test_retry_backup_job():
    trig = client.post("/api/v1/backups", json={"record_id": "EHR_10025"})
    job_id = trig.json()[0]["job_id"]

    retry_resp = client.post(f"/api/v1/backups/{job_id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["job_id"] == job_id
    assert retry_resp.json()["status"] == "COMPLETED"
