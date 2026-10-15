import os
import json
import pytest
from app.db.dynamodb import db_memory
from scripts.deploy_aws_resources import main as deploy_main
from scripts.teardown_aws_resources import main as teardown_main
from scripts.seed_data import seed_records


@pytest.fixture(autouse=True)
def clean_db():
    db_memory.clear()
    yield
    db_memory.clear()


def test_iam_policy_structure():
    """Verify least-privilege IAM policy document adheres to security constraints."""
    policy_path = os.path.join(os.path.dirname(__file__), "../aws/iam_policy.json")
    assert os.path.exists(policy_path)

    with open(policy_path, "r") as f:
        policy = json.load(f)

    assert policy["Version"] == "2012-10-17"
    statements = policy["Statement"]
    assert len(statements) >= 3

    # Check S3 least privilege
    s3_stmt = next(s for s in statements if s["Sid"] == "LeastPrivilegeS3Access")
    assert any("smart-hospital-ehr" in r for r in s3_stmt["Resource"])
    assert "s3:PutObject" in s3_stmt["Action"]
    assert "s3:GetObject" in s3_stmt["Action"]

    # Check DynamoDB least privilege
    ddb_stmt = next(s for s in statements if s["Sid"] == "LeastPrivilegeDynamoDBAccess")
    assert any("SmartHospitalRecords" in r for r in ddb_stmt["Resource"])


def test_deploy_and_teardown_dry_run():
    """Verify automated deployment and 1-click teardown scripts in dry-run mode."""
    # Test deployment
    deploy_res = deploy_main(dry_run=True)
    assert deploy_res["status"] == "SUCCESS"
    assert deploy_res["mode"] == "SIMULATION"

    # Test teardown
    teardown_res = teardown_main(dry_run=True)
    assert teardown_res["status"] == "SUCCESS"
    assert teardown_res["mode"] == "SIMULATION"


def test_seed_synthetic_data():
    """Verify synthetic hospital record seeding populates multi-tier records and access events."""
    seeded = seed_records()
    assert len(seeded) == 6

    # Verify presence in database
    records = db_memory.list_records()
    assert len(records) == 6

    # Verify access events were also seeded
    events = db_memory.list_access_events()
    assert len(events) == 6

    # Verify emergency flag and patient IDs
    crit = [r for r in records if r["criticality"] == "CRITICAL"]
    assert len(crit) >= 1
    assert all(r["patient_id"].startswith("P_SYN_") for r in records)
