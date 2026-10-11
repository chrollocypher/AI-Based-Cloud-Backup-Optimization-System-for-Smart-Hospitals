# Smart Hospital EHR Storage & Retrieval System: API Contracts & Architecture Specification

## Overview
This document defines the formal system architecture, storage tier mappings, and API contracts for the **AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System**. It establishes clean architectural boundaries across the three sub-teams:
- **Member A (AI/ML & Data)**: Synthea derivation, access & backup forecasting models (LSTM / BiLSTM).
- **Member B (Backend & AWS)**: API layer, DynamoDB persistence, S3 multi-tier operations, Step Functions orchestration, CloudWatch metrics.
- **Member C (Decision/Retrieval & UI)**: Storage cost policy, emergency retrieval rules, cache/prefetch optimization, evaluation benchmarks, React dashboard.

---

## 1. Cloud Storage Tier Mapping

Internal tier labels must map deterministically to concrete AWS S3 Storage Classes:

| Internal Tier Label | AWS S3 Storage Class | Target Latency | Min Storage Duration | Typical Hospital Use Case |
| :--- | :--- | :--- | :--- | :--- |
| `HOT` | `STANDARD` | < 100 ms | None | Active patient encounters, Emergency Room (ER) records, high access frequency. |
| `WARM` | `STANDARD_IA` | < 250 ms | 30 days | Discharged patients (< 30 days), inpatient baseline history, weekly review. |
| `COLD` | `GLACIER_FLEXIBLE` | 1–5 min (Expedited) / 3–5 hrs (Std) | 90 days | Historical archives, closed encounters (> 90 days), low predicted access. |
| `ARCHIVE` | `DEEP_ARCHIVE` | 12–48 hours | 180 days | Multi-year compliance archives, deceased patient records. |

> [!IMPORTANT]
> **Clinical Safety Guardrail**: Critical records (`criticality == 'CRITICAL'`) and records with active emergency flags (`emergency_flag == True`) must **never** be placed in `COLD` or `ARCHIVE` tiers if their emergency retrieval SLA (< 500 ms) cannot be satisfied.

---

## 2. Workload & Event Data Schemas

### 2.1 Raw Access-Event Log Schema
Every interaction with an EHR record produces an access event conforming to this schema:

```json
{
  "event_id": "EVT_948201",
  "timestamp": "2026-10-11T14:30:00Z",
  "patient_id": "P_SYN_10482",
  "record_type": "EHR",
  "department": "Emergency",
  "access_type": "RETRIEVE",
  "access_frequency": 14,
  "data_size_mb": 12.5,
  "criticality": "CRITICAL",
  "storage_tier": "STANDARD",
  "emergency_flag": true,
  "backup_status": null
}
```

- `access_type`: `READ` | `WRITE` | `UPDATE` | `RETRIEVE` | `BACKUP`
- `criticality`: `CRITICAL` (4) | `HIGH` (3) | `MEDIUM` (2) | `LOW` (1)
- `storage_tier`: `STANDARD` | `STANDARD_IA` | `GLACIER_FLEXIBLE` | `DEEP_ARCHIVE`
- `backup_status`: `PENDING` | `SCHEDULED` | `IN_PROGRESS` | `COMPLETED` | `FAILED` | `null`

### 2.2 Hourly Processed Workload Schema
Access and backup workloads are aggregated independently into 1-hour time windows:

```json
{
  "window_start_time": "2026-10-11T14:00:00Z",
  "access_event_count": 1420,
  "access_volume_mb": 18450.5,
  "backup_event_count": 85,
  "backup_volume_mb": 4210.0,
  "emergency_event_count": 48
}
```

---

## 3. API Endpoints Contract

### 3.1 Prediction & Workload Forecasting (ML $\leftrightarrow$ Backend)
- **POST `/api/v1/predictions/backup-volume`**
  - **Description**: Evaluates next-hour backup volume forecast using the preserved TensorFlow LSTM baseline model.
  - **Request**: `{"lookback_hours": 24, "historical_volume": [...]}`
  - **Response**: `{"forecast_hour": "...", "predicted_backup_volume_mb": 4210.0, "model_id": "lstm-backup-v1"}`

- **POST `/api/v1/predictions/access-demand`**
  - **Description**: Evaluates next-hour access event frequency and demand volume (Member A BiLSTM / LSTM model).
  - **Request**: `{"lookback_hours": 24, "historical_access_counts": [...]}`
  - **Response**: `{"forecast_hour": "...", "predicted_access_count": 1450, "predicted_access_volume_mb": 18900.0, "model_id": "bilstm-access-v1"}`

- **GET `/api/v1/workload/forecast-latest`**
  - **Description**: Returns joint next-hour workload (both backup volume and access demand) for orchestrator decision-making.

### 3.2 Records & Access Log Ingestion
- **POST `/api/v1/records`**
  - Create or ingest an EHR record metadata object.
- **GET `/api/v1/records/{record_id}`**
  - Fetch record metadata including current tier, last accessed timestamp, and criticality.
- **POST `/api/v1/records/access-events`**
  - Ingest raw access event logs (batch or single).
- **GET `/api/v1/records/patient/{patient_id}/access-history`**
  - Retrieve chronological access logs for a specific patient.

### 3.3 Storage Tiering & Decision Engine
- **POST `/api/v1/storage/tier-transitions`**
  - **Description**: Apply storage-tier migration rule (e.g., transition cold records from Standard to Standard-IA or Glacier).
  - **Request**: `{"record_id": "REC_101", "target_tier": "STANDARD_IA", "decision_reason": "Low predicted access demand"}`
  - **Response**: `{"record_id": "REC_101", "previous_tier": "STANDARD", "new_tier": "STANDARD_IA", "transitioned_at": "..."}`

- **GET `/api/v1/storage/cost-estimate`**
  - **Description**: Calculate estimated storage and retrieval costs across all records under AWS pricing.

### 3.4 Emergency Retrieval & SLA Tracking (Backend $\leftrightarrow$ Member C)
- **POST `/api/v1/records/{record_id}/retrieve`**
  - **Description**: High-priority retrieval request for hospital records.
  - **Request**: `{"is_emergency": true, "department": "Emergency", "reason": "Acute Trauma Assessment"}`
  - **Response**:
    ```json
    {
      "retrieval_id": "RET_738192",
      "record_id": "REC_101",
      "is_emergency": true,
      "storage_tier": "STANDARD",
      "cache_hit": true,
      "retrieval_latency_ms": 12.4,
      "sla_target_ms": 500.0,
      "sla_met": true,
      "retrieved_at": "2026-10-11T14:32:10.123Z",
      "s3_location": "s3://smart-hospital-records/ehr/REC_101.json"
    }
    ```

- **GET `/api/v1/retrieval/metrics`**
  - **Description**: Aggregate retrieval performance telemetry (average latency by tier, cache hit rate, emergency SLA violation rate).

---

## 4. Evaluation Metrics Alignment
All three members evaluate on identical trace periods using the 7 standardized metrics:
1. **Prediction Accuracy**: MAE, RMSE, MAPE (access and backup evaluated separately).
2. **Retrieval Latency**: Milliseconds from request to availability (Emergency vs Non-emergency, per tier).
3. **Storage Cost**: S3 storage fees + request fees + transition & early deletion penalties ($ USD).
4. **Critical Record Availability**: % of critical records retrieved within SLA.
5. **Cache/Prefetch Hit Rate**: Hits / Total retrieval requests.
6. **Backup Success Rate**: Completed backups / Attempted backups.
7. **SLA Violations**: Count and percentage of emergency requests exceeding 500 ms.
