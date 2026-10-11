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
    DYNAMODB_TABLE_ACCESS_EVENTS: str = "SmartHospitalAccessEvents"
    DYNAMODB_TABLE_RETRIEVALS: str = "SmartHospitalRetrievalJobs"

    # Step Functions & SageMaker
    STEP_FUNCTION_ARN: str = "arn:aws:states:us-east-1:123456789012:stateMachine:SmartHospitalBackupPipeline"
    SAGEMAKER_ENDPOINT_NAME: str = ""

    # Operational Thresholds
    CAPACITY_THRESHOLD_MB: float = 10000.0

    # ML Model & Dataset Settings
    MODEL_PATH: str = "src/ml_model/models/best_lstm_model.keras"
    ACCESS_MODEL_PATH: str = "src/ml_model/models/best_access_bilstm.keras"
    WORKLOAD_DATA_PATH: str = "dataset/processed/workload_timeseries_1h.csv"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
