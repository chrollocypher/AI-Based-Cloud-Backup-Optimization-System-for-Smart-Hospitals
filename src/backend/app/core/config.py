from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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

    # Step Functions & SageMaker
    STEP_FUNCTION_ARN: str = "arn:aws:states:us-east-1:123456789012:stateMachine:SmartHospitalBackupPipeline"
    SAGEMAKER_ENDPOINT_NAME: str = ""

    # Operational Thresholds
    CAPACITY_THRESHOLD_MB: float = 10000.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
