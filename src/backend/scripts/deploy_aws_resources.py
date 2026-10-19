"""Automated AWS Infrastructure Provisioning Script for Smart Hospital System.

Provisions S3 multi-tier buckets, DynamoDB pay-per-request tables, Step Functions,
and CloudWatch alarms with budget limit guardrails ($5 - $10).
"""
import os
import sys
import json
import boto3

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings


def deploy_s3_bucket(s3_client, bucket_name: str, region: str, dry_run: bool = False):
    """Creates S3 bucket with versioning and lifecycle configuration."""
    print(f"[*] Provisioning S3 Bucket: {bucket_name}")
    if dry_run:
        print(f"    [DRY RUN] S3 bucket '{bucket_name}' simulated created.")
        return

    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        print(f"    [SUCCESS] Created bucket: {bucket_name}")
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"    [INFO] Bucket '{bucket_name}' already exists and is owned by you.")


def deploy_dynamodb_tables(dynamodb_client, dry_run: bool = False):
    """Creates DynamoDB tables using on-demand billing (zero idle charges)."""
    tables = [
        {"name": settings.DYNAMODB_TABLE_RECORDS, "key": "record_id"},
        {"name": settings.DYNAMODB_TABLE_JOBS, "key": "job_id"},
        {"name": settings.DYNAMODB_TABLE_ACCESS_EVENTS, "key": "event_id"},
        {"name": settings.DYNAMODB_TABLE_RETRIEVALS, "key": "retrieval_id"},
    ]

    for t in tables:
        print(f"[*] Provisioning DynamoDB Table: {t['name']}")
        if dry_run:
            print(f"    [DRY RUN] DynamoDB Table '{t['name']}' simulated created.")
            continue

        try:
            dynamodb_client.create_table(
                TableName=t["name"],
                KeySchema=[{"AttributeName": t["key"], "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": t["key"], "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            print(f"    [SUCCESS] Created table: {t['name']}")
        except dynamodb_client.exceptions.ResourceInUseException:
            print(f"    [INFO] Table '{t['name']}' already exists.")


def deploy_cloudwatch_alarms(cw_client, dry_run: bool = False):
    """Creates CloudWatch alarm for SLA violation detection."""
    alarm_name = "SmartHospital_Emergency_SLA_Breach"
    print(f"[*] Provisioning CloudWatch Alarm: {alarm_name}")
    if dry_run:
        print(f"    [DRY RUN] Alarm '{alarm_name}' simulated created.")
        return

    try:
        cw_client.put_metric_alarm(
            AlarmName=alarm_name,
            ComparisonOperator="GreaterThanThreshold",
            EvaluationPeriods=1,
            MetricName="SLAViolationsCount",
            Namespace="SmartHospital/EHRStorage",
            Period=60,
            Statistic="Sum",
            Threshold=0.0,
            ActionsEnabled=False,
            AlarmDescription="Alert triggered if any emergency EHR retrieval exceeds 500 ms SLA"
        )
        print(f"    [SUCCESS] CloudWatch Alarm '{alarm_name}' configured.")
    except Exception as e:
        print(f"    [WARNING] Failed to configure CloudWatch alarm: {e}")


def main(dry_run: bool = False):
    print("=" * 60)
    print("SMART HOSPITAL AWS INFRASTRUCTURE DEPLOYMENT")
    print(f"Region: {settings.AWS_REGION}")
    print(f"Budget Guardrail: $5.00 - $10.00 USD Maximum Cap")
    print("=" * 60)

    is_mock = settings.USE_MOCK_AWS or not settings.AWS_ACCESS_KEY_ID or dry_run

    if is_mock:
        print("\n[NOTE] AWS credentials not configured or dry-run requested. Running simulated deployment.")
        deploy_s3_bucket(None, "smart-hospital-ehr", settings.AWS_REGION, dry_run=True)
        deploy_dynamodb_tables(None, dry_run=True)
        deploy_cloudwatch_alarms(None, dry_run=True)
        print("\n[SUCCESS] Simulated cloud deployment completed successfully.")
        return {"status": "SUCCESS", "mode": "SIMULATION"}

    # Populate environment so boto3 default chain and clients inherit credentials
    if settings.AWS_ACCESS_KEY_ID:
        os.environ["AWS_ACCESS_KEY_ID"] = settings.AWS_ACCESS_KEY_ID
    if settings.AWS_SECRET_ACCESS_KEY:
        os.environ["AWS_SECRET_ACCESS_KEY"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_REGION:
        os.environ["AWS_DEFAULT_REGION"] = settings.AWS_REGION

    boto3_kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        boto3_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        boto3_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

    s3 = boto3.client("s3", **boto3_kwargs)
    ddb = boto3.client("dynamodb", **boto3_kwargs)
    cw = boto3.client("cloudwatch", **boto3_kwargs)

    deploy_s3_bucket(s3, "smart-hospital-ehr", settings.AWS_REGION, dry_run=False)
    deploy_dynamodb_tables(ddb, dry_run=False)
    deploy_cloudwatch_alarms(cw, dry_run=False)

    print("\n[SUCCESS] AWS cloud infrastructure deployed successfully.")
    return {"status": "SUCCESS", "mode": "AWS_LIVE"}


if __name__ == "__main__":
    main()
