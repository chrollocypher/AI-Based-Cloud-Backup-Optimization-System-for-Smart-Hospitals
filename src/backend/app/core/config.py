import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Hospital Cloud Backup Optimization Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # AWS Settings
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    USE_MOCK_AWS: bool = True

    # DynamoDB Table Names
    DYNAMODB_TABLE_RECORDS: str = "SmartHospitalRecords"
    DYNAMODB_TABLE_JOBS: str = "SmartHospitalBackupJobs"
    DYNAMODB_TABLE_ACCESS_EVENTS: str = "SmartHospitalAccessEvents"
    DYNAMODB_TABLE_RETRIEVALS: str = "SmartHospitalRetrievalJobs"

    # Step Functions & SageMaker
    STEP_FUNCTION_ARN: str = "arn:aws:states:us-east-1:123456789012:stateMachine:SmartHospitalBackupPipeline"
    SAGEMAKER_ENDPOINT_NAME: str = ""

    # Operational Thresholds
    CAPACITY_THRESHOLD_MB: float = 10000.0

    # ML Model & Dataset Settings
    MODEL_PATH: str = "src/ml_model/synthetic_ehr/models/best_synthea_backup_lstm.keras"
    ACCESS_MODEL_PATH: str = "src/ml_model/synthetic_ehr/models/best_synthea_access_lstm.keras"
    WORKLOAD_DATA_PATH: str = "dataset/synthea/processed/synthea_hourly_workload.csv"
    SYNTHEA_ACCESS_LOGS_PATH: str = "dataset/synthea/processed/synthea_ehr_access_logs.csv"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Automatically propagate AWS credentials from settings into os.environ for all boto3 clients
if settings.AWS_ACCESS_KEY_ID:
    os.environ["AWS_ACCESS_KEY_ID"] = settings.AWS_ACCESS_KEY_ID
if settings.AWS_SECRET_ACCESS_KEY:
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.AWS_SECRET_ACCESS_KEY
if settings.AWS_REGION:
    os.environ["AWS_DEFAULT_REGION"] = settings.AWS_REGION

