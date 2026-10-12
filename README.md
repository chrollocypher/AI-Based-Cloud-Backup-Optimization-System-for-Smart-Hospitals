# AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System

An enterprise-grade, predictive cloud optimization system for Smart Hospitals that dynamically forecasts electronic health record (EHR) retrieval access patterns and automated cloud backup workloads, orchestrating capacity-aware scheduling, emergency awareness, and multi-cycle queue management.

---

## 1. Environment Setup

### Prerequisites
- **Python Version:** Python 3.11 (tested and verified with Python 3.11.9 on Windows / Linux / macOS).
- **Core Dependencies:** Listed in `requirements.txt`:
  - `tensorflow>=2.15.0` (verified with TensorFlow 2.21.0)
  - `pandas>=2.0.0` (verified with Pandas 3.0.6)
  - `numpy>=1.24.0` (verified with NumPy 2.4.6)

### Setup Instructions
Create and activate a virtual environment, then install requirements:

```bash
# Create virtual environment
python -m venv .venv-ml

# Activate virtual environment
# Windows (PowerShell):
.\.venv-ml\Scripts\Activate.ps1
# Windows (cmd):
.\.venv-ml\Scripts\activate.bat
# Linux / macOS:
source .venv-ml/bin/activate

# Install direct project requirements
pip install -r requirements.txt
```

---

## 2. Architecture Overview

```
                               ┌──────────────────────────────────────────────┐
                               │       Official Synthea Patient Records       │
                               │  (Encounters, Observations, Procedures, etc.)│
                               └──────────────────────┬───────────────────────┘
                                                      │
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │       Synthea EHR Transformation Pipeline    │
                               │   - Causal 30-day Access Frequency           │
                               │   - 12 Standard Schema Fields                │
                               │   - Decoupled Access vs. Backup Workloads    │
                               └──────────────────────┬───────────────────────┘
                                                      │
                         ┌────────────────────────────┴────────────────────────────┐
                         ▼                                                         ▼
         ┌───────────────────────────────┐                         ┌───────────────────────────────┐
         │     Access Workload LSTM      │                         │     Backup Workload LSTM      │
         │   (Retrieval Bandwidth AI)    │                         │    (Cloud Backup Capacity AI) │
         └───────────────┬───────────────┘                         └───────────────┬───────────────┘
                         │                                                         │
                         └────────────────────────────┬────────────────────────────┘
                                                      ▼
                               ┌──────────────────────────────────────────────┐
                               │           AI Orchestration Engine            │
                               │  1. Priority Engine (CRITICAL to LOW)        │
                               │  2. Capacity-Aware Greedy Scheduler          │
                               │  3. Persistent Deferred Queue                │
                               └──────────────────────────────────────────────┘
```

---

## 3. Approved ML Components (`src/ml_model/`)

The machine learning subsystem relies strictly on the official **MITRE Synthea™** public healthcare dataset as its sole underlying data source.

### Active ML Modules
- **`src/ml_model/synthetic_ehr/`**: The core approved ML pipeline:
  - `ehr_transformer.py`: Maps Synthea tables into 12-field EHR access logs with zero future lookahead leakage.
  - `workload_aggregator.py`: Decouples access demand from backup replication demand into daily/hourly series.
  - `data_loader.py`: Enforces strict 70/15/15 chronological splitting and leak-free `SyntheaWorkloadScaler` fitting.
  - `lstm_train.py`: Trains dedicated LSTMs from scratch for both workload targets.
  - `evaluate.py`: Benchmarks against Naive Persistence and 7-Day Moving Average baselines on identical holdout dates. Supports optional row-level prediction export.
  - `integration_adapter.py`: Bridges Synthea EHR records to the scheduling and priority engines.
  - `test_synthea_pipeline.py`: Comprehensive 8-test suite verifying causality, boundaries, reproducibility, scheduling, and prediction export invariance.
- **`src/ml_model/priority/`**: Deterministic explainable priority assignment (`priority_policy.py`).
- **`src/ml_model/scheduler/`**: Capacity-aware greedy backup scheduling engine (`scheduler.py`).
- **`src/ml_model/queue/`**: Multi-cycle persistent deferred backup queue (`pending_queue.py`).

### Validated Model Checkpoints (`src/ml_model/synthetic_ehr/models/`)
- `best_synthea_backup_lstm.keras` & `synthea_backup_scaler.json`: Validated model for daily cloud backup volume.
- `best_synthea_access_lstm.keras` & `synthea_access_scaler.json`: Validated model for daily EHR retrieval bandwidth.

### Historical Archive (`archive/legacy_custom_model/`)
All exploratory artifacts from the early custom-generated dataset have been quarantined into `archive/legacy_custom_model/`. They are strictly excluded from all active training, evaluation, and inference paths.

---

## 4. Modeling Protocol & Holdout Evaluation Benchmarks

### Training & Split Protocol
- **Sequence Lookback Window:** Exactly 14 days ($t - 14$ to $t - 1$ predicting day $t$).
- **Partitioning:** Chronological 70% Train (1,694 days), 15% Validation (363 days), 15% Holdout Test (364 days). No shuffle.
- **Scaling:** `SyntheaWorkloadScaler` MinMax parameters fitted strictly on the 70% training split.

### Benchmark Results (364 Holdout Days: 2025-08-19 to 2026-08-17)
Complete summary metrics persisted in `results/synthea_evaluation_metrics.json`:

#### Target 1: Cloud Backup Workload (`backup_workload_mb`)
| Model / Baseline | MAE (MB) | RMSE (MB) | WAPE (%) | Filtered MAPE ($> 1\text{ MB}$) | Outcome Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **LSTM (Dedicated)** | **25.93** 🏆 | **35.72** 🏆 | **81.83%** 🏆 | 195.64% | **Wins on MAE, RMSE, and WAPE** |
| **Baseline: 7-Day Moving Avg** | 28.53 | 39.68 | 90.02% | **178.71%** 🏆 | Wins on Filtered MAPE |
| **Baseline: Naive Persistence**| 33.99 | 51.21 | 107.27% | 187.81% | Third place across all metrics |

#### Target 2: EHR Access / Retrieval Workload (`access_workload_mb`)
| Model / Baseline | MAE (MB) | RMSE (MB) | WAPE (%) | Filtered MAPE ($> 1\text{ MB}$) | Outcome Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **LSTM (Dedicated)** | **25.68** 🏆 | **36.19** 🏆 | **76.01%** 🏆 | **163.02%** 🏆 | **Wins on all 4 metrics** |
| **Baseline: 7-Day Moving Avg** | 29.96 | 41.14 | 88.68% | 176.43% | Second place |
| **Baseline: Naive Persistence**| 35.86 | 53.29 | 106.14% | 184.87% | Third place |

### Metric Definitions
- **MAE (Mean Absolute Error, MB):** Scale-dependent primary error $\frac{1}{N} \sum |y - \hat{y}|$.
- **RMSE (Root Mean Squared Error, MB):** Heavily penalizes large deviation spikes $\sqrt{\frac{1}{N} \sum (y - \hat{y})^2}$.
- **WAPE (Weighted Absolute Percentage Error, %):** $\frac{\sum |y - \hat{y}|}{\sum y} \times 100$. Well-behaved with intermittent zero days.
- **Filtered MAPE (%):** Computed on $y_{\text{true}} > 1.0\text{ MB}$ to avoid division-by-zero instability on low-volume days.

---

## 5. Supported Commands

All commands should be executed from the workspace root using the virtual environment:

### A. Run Automated Unit & Regression Tests (8 Tests)
```bash
python -m unittest -v src/ml_model/synthetic_ehr/test_synthea_pipeline.py
```

### B. Evaluate Existing Saved Models against Baselines
```bash
python src/ml_model/synthetic_ehr/evaluate.py
```
*(Loads saved checkpoints and scalers, validates existing metrics JSON, and displays comparative scorecard).*

### C. Evaluate with Optional Row-Level Prediction Export
```bash
python src/ml_model/synthetic_ehr/evaluate.py --export-predictions
```
*(Exports 728 row-level holdout predictions across both targets to `results/synthea_test_predictions.csv`).*

### D. Transform Raw Synthea Records to EHR Access Logs
```bash
python src/ml_model/synthetic_ehr/ehr_transformer.py
```

### E. Generate Decoupled Workload Time Series
```bash
python src/ml_model/synthetic_ehr/workload_aggregator.py
```

### F. Run Priority Policy and Scheduler Integration Demos
```bash
python src/ml_model/priority/priority_demo.py
python src/ml_model/scheduler/scheduler_demo.py
python src/ml_model/queue/queue_demo.py
```

---

## 6. Output Files & Dataset Description

| File Path | Description | Units / Schema |
| :--- | :--- | :--- |
| `dataset/synthea/processed/synthea_ehr_access_logs.csv` | Transformed EHR event logs (64,676 records) | 12 fields (event ID, timestamp, patient ID, record type, dept, access type, access freq, size MB, criticality, tier, emergency flag, backup status) |
| `dataset/synthea/processed/synthea_daily_workload.csv` | Daily aggregated continuous time series (2,421 days) | `window_start_time`, `backup_workload_mb` (MB), `access_workload_mb` (MB), `emergency_event_count`, `total_event_count` |
| `dataset/synthea/processed/synthea_hourly_workload.csv`| Hourly aggregated continuous time series (58,081 hours)| Same as daily series, hourly resolution |
| `results/synthea_evaluation_metrics.json` | Final comparative benchmark scorecard | JSON object containing MAE, RMSE, WAPE, filtered MAPE, and winner per metric |
| `results/synthea_test_predictions.csv` | (Optional export) Row-level holdout predictions | `window_start_time`, `target_name`, `actual_workload_mb` (MB), `predicted_lstm_mb` (MB), `predicted_naive_mb` (MB), `predicted_moving_average_mb` (MB) |

---

## 7. Important Research Limitations & Academic Disclosure

> [!NOTE]
> **Source-Derived Clinical Data vs. Simulated Systems Behavior:**
> - **Synthea provides realistic clinical healthcare history:** Patient encounters, clinical diagnoses, lab observation values, medications, imaging studies, and procedure timelines.
> - **Synthea does NOT provide IT storage or cloud access logs:** File sizes (`data_size_mb`), EMR interaction types (`access_type`), cloud storage tiers (`storage_tier`), and cloud replication states (`backup_status`) are explicitly modeled based on standard healthcare imaging standards and operational hospital workflows.
> - Emergency flags are source-derived from Synthea acute care admissions (`ENCOUNTERCLASS in ['emergency', 'urgentcare']`), but operational criticality levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) are assigned by explainable heuristic policy rules for cloud scheduling, not as formal medical diagnoses.
