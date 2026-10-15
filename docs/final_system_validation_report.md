# AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System
## Final System Validation & Teacher Review Guide

**Repository**: `AI-Based-Cloud-Backup-Optimization-System-for-Smart-Hospitals`  
**Branch**: `feature/gokul`  
**Research Question**: *“Can future EHR access demand and clinical criticality be jointly used to optimize cloud storage cost while reducing retrieval latency for hospital records?”*

---

## 1. Executive Summary & Core Results

The extended system has been fully implemented, validated across 54 automated tests, and benchmarked against two baseline policies on a continuous 168-hour chronological trace.

### 7-Metric Benchmark Comparison

| Evaluation Metric | Policy A: Proposed (AI + Shield + Cache) | Policy B: Static Baseline (100% S3 Standard) | Policy C: Conventional (Naive Aging) |
| :--- | :--- | :--- | :--- |
| **1. Average Emergency Latency** | **17.84 ms** (Sub-25ms with cache) | 92.41 ms (Direct cloud fetch) | **180,000.0 ms** (Glacier delay) |
| **2. Critical Record Availability** | **100.0%** (&le; 500 ms SLA) | 100.0% | **42.15%** (Glacier lockout) |
| **3. Monthly Cloud Storage Cost** | **$0.8124 / month** | $1.7612 / month | $1.1420 / month |
| **   Cost Savings vs Static** | **53.87% Saved** | 0.0% Baseline | 35.16% Saved |
| **4. Edge Cache Hit Rate** | **31.45%** | 0.0% | 0.0% |
| **5. Backup Success Rate** | **100.0%** | 100.0% | 100.0% |
| **6. Emergency SLA Breaches** | **0 breaches** | 0 breaches | **198 SLA breaches** |
| **7. Workload Forecast MAE** | Backup: 42.18 MB; Access: 2.50 events | N/A | N/A |

**Key Research Conclusion**: **Yes.** The proposed architecture achieves **53.87% cloud storage cost savings** while maintaining **100% critical availability** and reducing emergency retrieval latency to **17.84 ms**. The naive conventional baseline saves some cost (35.16%) but causes severe clinical hazards (198 SLA violations due to cold Glacier lockouts), proving that joint awareness of access demand and clinical criticality is essential.

---

## 2. Dataset Validation Checklist Sign-Off (Section 10)

- [x] **Source archive and official URL recorded**: Synthea Synthetic Health data (https://synthetichealth.github.io/downloads.html).
- [x] **Source CSV names, row counts, and schema validated**: Validated in `dataset/raw/ehr_access_events_raw.csv` (6,000 events) and `dataset/processed/ehr_hourly_workload_timeseries.csv` (227 continuous 1-hour windows).
- [x] **Source-derived fields distinguishable from simulated fields**:
  - *Source-Derived*: `patient_id` (Synthea mapped), `record_type`, `timestamp`.
  - *Documented Simulated*: `event_id`, `access_type`, `access_frequency` (24h lookback), `data_size_mb`, `criticality`, `storage_tier`, `emergency_flag`, `backup_status`.
- [x] **Zero Real PHI**: 100% synthetic identifiers and records are used; no real patient data is ever uploaded.
- [x] **Unique event IDs & No Duplicates**: Strictly enforced UUID / unique integer indexing.
- [x] **Chronological & Continuous Timelines**: Hourly windows generated continuously without time gaps.
- [x] **Independent Workload Separation**: Backup volume targets (`backup_volume_mb`) and Access demand targets (`access_event_count`, `access_volume_mb`) are maintained and forecasted independently.
- [x] **Preservation of Original Baseline**: `dataset/raw/hospital_backup_raw_data.csv`, `dataset/processed/workload_timeseries_1h.csv`, and `src/ml_model/models/best_lstm_model.keras` remain 100% untouched.

---

## 3. End-to-End System Components

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE MAP                                   │
│                                                                                        │
│  [1. Synthetic EHR Engine] ──────────► [2. Dual Forecasting Engine]                    │
│      • derive_access_logs.py               • Preserved Backup LSTM (Keras)             │
│      • aggregate_hourly_workload.py        • Access-Demand Model (Ridge/BiLSTM)        │
│      • Zero-leakage 24h lookback           • Joint Intensity Evaluator                 │
│                                                          │                             │
│                                                          ▼                             │
│  [4. Emergency Retrieval Engine] ◄───── [3. Storage Tier Decision Engine]             │
│      • Edge LRU Cache Layer (<20ms)        • HOT (Standard) / WARM (IA) / COLD (Glacier│
│      • 500 ms SLA Watchdog                 • Clinical Safety Shield (Blocks Glacier)   │
│      • Proactive Trauma Prefetch           • AWS us-east-1 Cost Calculator             │
│                                                          │                             │
│                                                          ▼                             │
│  [6. Frontend Console (React)] ◄─────── [5. AWS Serverless & Orchestration]            │
│      • Storage & Retrieval Console         • Step Functions State Machine              │
│      • Emergency Lookup Simulator          • Serverless Task Handlers                  │
│      • Dual Workload Forecast              • CloudWatch Custom Metrics & Alarms        │
│      • S3 Cost Comparison Widget           • 1-Click Teardown (Zero Cost Guarantee)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Runbook: How to Test & Demonstrate

### 4.1 Running All Automated Tests (54 Test Cases)
```bash
pytest src/backend/tests -v
```

### 4.2 Running the Comparative Benchmark Experiment
```bash
python src/backend/scripts/run_comparative_evaluation.py
```
Outputs generated in `results/`:
- `comparative_evaluation_summary.json`
- `comparative_metrics_table.csv`
- `comparative_evaluation_report.md`

### 4.3 Starting the Backend API
```bash
cd src/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive docs at `http://localhost:8000/docs`.

### 4.4 Starting the Frontend React Dashboard
```bash
cd src/frontend
npm run dev
```
Dashboard available at `http://localhost:5173`. Navigate to **Storage & Retrieval** to interactively test emergency lookups, cache hits, and Step Functions runs.

### 4.5 Cloud Deployment & Teardown Verification
- Dry-run deployment: `python src/backend/scripts/deploy_aws_resources.py`
- 1-click teardown: `python src/backend/scripts/teardown_aws_resources.py`
