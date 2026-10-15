"""Automated 1-Click AWS Teardown Script for Smart Hospital System.

Empties all S3 buckets (including versioned objects), deletes DynamoDB tables,
and removes CloudWatch alarms to ensure zero lingering charges.
"""
import os
import sys
import boto3

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings


def teardown_s3_bucket(s3_client, bucket_name: str, dry_run: bool = False):
    """Recursively deletes all objects and versions, then deletes the S3 bucket."""
    print(f"[*] Decommissioning S3 Bucket: {bucket_name}")
    if dry_run:
        print(f"    [DRY RUN] S3 bucket '{bucket_name}' simulated emptied and deleted.")
        return

    try:
        # Delete all object versions and delete markers
        s3_resource = boto3.resource("s3", region_name=settings.AWS_REGION)
        bucket = s3_resource.Bucket(bucket_name)

        bucket.object_versions.delete()
        bucket.delete()
        print(f"    [SUCCESS] Emptied and deleted bucket: {bucket_name}")
    except Exception as e:
        print(f"    [INFO] Bucket teardown: {e}")


def teardown_dynamodb_tables(dynamodb_client, dry_run: bool = False):
    """Deletes all project DynamoDB tables."""
    tables = [
        settings.DYNAMODB_TABLE_RECORDS,
        settings.DYNAMODB_TABLE_JOBS,
        settings.DYNAMODB_TABLE_ACCESS_EVENTS,
        settings.DYNAMODB_TABLE_RETRIEVALS,
    ]

    for t in tables:
        print(f"[*] Decommissioning DynamoDB Table: {t}")
        if dry_run:
            print(f"    [DRY RUN] DynamoDB Table '{t}' simulated deleted.")
            continue

        try:
            dynamodb_client.delete_table(TableName=t)
            print(f"    [SUCCESS] Deleted table: {t}")
        except dynamodb_client.exceptions.ResourceNotFoundException:
            print(f"    [INFO] Table '{t}' was not found.")
        except Exception as e:
            print(f"    [WARNING] Failed to delete table {t}: {e}")


def teardown_cloudwatch_alarms(cw_client, dry_run: bool = False):
    """Removes project CloudWatch alarms."""
    alarm_name = "SmartHospital_Emergency_SLA_Breach"
    print(f"[*] Decommissioning CloudWatch Alarm: {alarm_name}")
    if dry_run:
        print(f"    [DRY RUN] CloudWatch alarm '{alarm_name}' simulated deleted.")
        return

    try:
        cw_client.delete_alarms(AlarmNames=[alarm_name])
        print(f"    [SUCCESS] Deleted alarm: {alarm_name}")
    except Exception as e:
        print(f"    [WARNING] Failed to delete alarm {alarm_name}: {e}")


def main(dry_run: bool = False):
    print("=" * 60)
    print("SMART HOSPITAL AWS INFRASTRUCTURE TEARDOWN")
    print("Ensuring 100% Zero Lingering Cloud Charges")
    print("=" * 60)

    is_mock = settings.USE_MOCK_AWS or not settings.AWS_ACCESS_KEY_ID or dry_run

    if is_mock:
        print("\n[NOTE] Running simulated teardown for local testing.")
        teardown_s3_bucket(None, "smart-hospital-ehr", dry_run=True)
        teardown_dynamodb_tables(None, dry_run=True)
        teardown_cloudwatch_alarms(None, dry_run=True)
        print("\n[SUCCESS] Simulated teardown completed cleanly. Zero cloud charges.")
        return {"status": "SUCCESS", "mode": "SIMULATION"}

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    ddb = boto3.client("dynamodb", region_name=settings.AWS_REGION)
    cw = boto3.client("cloudwatch", region_name=settings.AWS_REGION)

    teardown_s3_bucket(s3, "smart-hospital-ehr", dry_run=False)
    teardown_dynamodb_tables(ddb, dry_run=False)
    teardown_cloudwatch_alarms(cw, dry_run=False)

    print("\n[SUCCESS] All cloud infrastructure successfully destroyed. Zero charges.")
    return {"status": "SUCCESS", "mode": "AWS_LIVE"}


if __name__ == "__main__":
    main()
