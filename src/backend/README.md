# Smart Hospital EHR Cloud Backend & AWS Engine

AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System.

---

## 1. Overview & Architecture

This service acts as the central API gateway, cloud storage engine, and serverless workflow orchestrator for the Smart Hospital EHR Storage & Retrieval System.

```
                          ┌─────────────────────────────────────┐
                          │     React Dashboard (Member C)      │
                          └──────────────────┬──────────────────┘
                                             │ HTTP REST
                                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Backend (Member B)                              │
│                                                                                        │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  ┌───────────────────────┐  │
│  │ Dual Forecasting Engine │  │ S3 Multi-Tier Engine     │  │ Emergency Retrieval   │  │
│  │ • Backup LSTM (Model A) │  │ • S3 Standard (HOT)      │  │ • Fast Edge Cache     │  │
│  │ • Access BiLSTM Adapter │  │ • Standard-IA (WARM)     │  │ • 500 ms SLA Watchdog │  │
│  │ • Joint Intensity Model │  │ • Glacier Flex (COLD)    │  │ • Latency Telemetry   │  │
│  └─────────────────────────┘  └──────────────────────────┘  └───────────────────────┘  │
│                                             │                                          │
│                    ┌────────────────────────┴─────────────────────────┐                │
│                    ▼                                                  ▼                │
│       AWS Step Functions Orchestration                    DynamoDB Multi-Table Store   │
│       • Pipeline State Machine                            • EHR Metadata               │
│       • Serverless Task Handlers                          • Access Event Logs          │
│       • CloudWatch Alarms & SNS                           • Retrieval SLA Audit        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Quickstart & Local Setup

### 2.1 Prerequisites
- Python 3.11+
- Virtual Environment

### 2.2 Installation & Launch
```bash
# Navigate to backend directory
cd src/backend

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3. Core API Endpoints

### 3.1 Workload Forecasting (ML $\leftrightarrow$ Backend)
- `POST /api/v1/predictions/backup-volume`: Evaluates next-hour backup volume forecast using the preserved LSTM model.
- `POST /api/v1/predictions/access-demand`: Forecasts hourly access event frequency, volume, and emergency spikes.
- `GET /api/v1/predictions/joint-forecast`: Returns combined forecast and operational intensity recommendation (`LOW`, `NORMAL`, `HIGH`, `PEAK`).

### 3.2 S3 Multi-Tier Storage & Cost Evaluation
- `POST /api/v1/storage/tier-transitions`: Executes storage-class migration adhering to clinical safety rules (blocks archiving `CRITICAL` or emergency records to Glacier).
- `GET /api/v1/storage/cost-estimate?region=us-east-1`: Computes itemized storage, request, and retrieval costs comparing proposed tiering policy against a static S3 Standard baseline.

### 3.3 Emergency Retrieval & Cache Engine
- `POST /api/v1/retrieval/request`: Executes high-priority record retrieval, checks in-memory cache, measures latency, and validates adherence to the 500 ms emergency SLA.
- `POST /api/v1/retrieval/prefetch`: Proactively warms the cache with predicted high-demand record IDs.
- `GET /api/v1/retrieval/metrics`: Aggregates retrieval telemetry (cache hit rate %, SLA violations, average latency by tier).

### 3.4 AWS Step Functions Orchestration
- `POST /api/v1/orchestration/trigger-pipeline`: Triggers the end-to-end pipeline: `Forecast -> Decide Tiers -> Execute S3 Transitions -> Publish Metrics`.
- `GET /api/v1/orchestration/executions`: Lists execution histories and step outputs.

### 3.5 Monitoring & Telemetry
- `GET /api/v1/monitoring/system-telemetry`: Returns all 7 standardized research evaluation metrics.
- `POST /api/v1/monitoring/cloudwatch/publish`: Publishes custom metrics to AWS CloudWatch namespace `SmartHospital/EHRStorage`.
- `GET /api/v1/monitoring/cloudwatch/alarms`: Inspects CloudWatch alarms and clinical SLA threshold breaches.

---

## 4. Operational Scripts

### 4.1 Seed Synthetic Data
Populates synthetic hospital records and access event traces:
```bash
python scripts/seed_data.py
```

### 4.2 Automated AWS Deployment (IaC)
Provisions S3 multi-tier buckets, pay-per-request DynamoDB tables, and CloudWatch alarms with budget guardrails ($5–$10 USD max cap):
```bash
python scripts/deploy_aws_resources.py
```

### 4.3 1-Click AWS Teardown
Empties all S3 buckets, removes version markers, deletes DynamoDB tables, and tears down all cloud infrastructure ensuring **100% zero ongoing charges**:
```bash
python scripts/teardown_aws_resources.py
```

---

## 5. Mock vs Live AWS Toggle
In `.env` or system environment:
- `USE_MOCK_AWS=True`: Runs high-fidelity simulation locally without requiring an AWS account or incurring any cloud costs.
- `USE_MOCK_AWS=False`: Connects to live AWS services using standard AWS credentials and region settings.
