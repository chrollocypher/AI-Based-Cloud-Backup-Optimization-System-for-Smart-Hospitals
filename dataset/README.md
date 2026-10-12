# Smart Hospital EHR Dataset Directory

This directory contains the underlying dataset sources and derived workload datasets used for the **AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System**.

## Approved Dataset: Official Synthea Public Healthcare Dataset

In accordance with academic requirements, the project strictly uses the public **MITRE Synthea™** dataset (`dataset/synthea/`) as the sole underlying clinical record source for all final modeling and experiments.

### 1. Source Clinical Tables (`dataset/synthea/`)

The following 18 official Synthea CSV tables were acquired and verified:
- `patients.csv` (108 synthetic patient master profiles, UUID identifiers, zero real PHI)
- `encounters.csv` (5,571 clinical encounters including ambulatory, emergency, inpatient, urgent care)
- `observations.csv` (68,648 clinical vitals, lab measurements, assessments)
- `conditions.csv` (3,517 diagnoses and chronic conditions)
- `medications.csv` (3,850 prescriptions and drug dispensation records)
- `imaging_studies.csv` (478 radiology and diagnostic imaging records)
- `procedures.csv` (15,884 clinical interventions and screenings)
- Additional tables: `allergies.csv`, `careplans.csv`, `devices.csv`, `supplies.csv`, `immunizations.csv`, `claims.csv`, `claims_transactions.csv`, `providers.csv`, `payers.csv`, `organizations.csv`, `payer_transitions.csv`

---

### 2. Derived Workload Datasets (`dataset/synthea/processed/`)

The transformation pipeline in `src/ml_model/synthetic_ehr/ehr_transformer.py` processes the raw Synthea records into standardized EHR access logs, which are then aggregated into decoupled time series by `src/ml_model/synthetic_ehr/workload_aggregator.py`.

#### A. Derived EHR Access Logs (`synthea_ehr_access_logs.csv`)
- **Total Records:** 64,676 events (dense 2020 to August 2026 longitudinal period).
- **Supported Schema (12 Fields):**
  1. `event_id`: Unique deterministically generated identifier (`EHR_<index>_<hash>`).
  2. `timestamp`: Direct UTC clinical event timestamp from Synthea.
  3. `patient_id`: Synthea synthetic patient UUID.
  4. `record_type`: Synthea clinical category (`OBSERVATION`, `PROCEDURE`, `ENCOUNTER`, `MEDICATION`, `IMAGING_STUDY`).
  5. `department`: Mapped clinical department (`LAB`, `ER`, `SURG`, `OPD`, `ICU`, `RAD`, `GEN`).
  6. `access_type`: Simulated EMR access operation (`WRITE`, `READ`, `UPDATE`, `QUERY_BATCH`, `EMERGENCY_OVERRIDE`).
  7. `access_frequency`: Strictly backward-looking count of prior events for the same patient in the preceding 30 days: $[T - 30\text{ days}, T)$. No future lookahead leakage.
  8. `data_size_mb`: Parametric sizing based on medical imaging and clinical payload standards.
  9. `criticality`: Deterministic operational priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
  10. `storage_tier`: Cloud storage lifecycle tier (`HOT`, `WARM`, `COLD`, `ARCHIVE`).
  11. `emergency_flag`: Source-derived indicator (`1` for emergency/urgentcare admissions; `0` otherwise).
  12. `backup_status`: Cloud replication state (`PENDING` for new writes/updates requiring cloud backup vs `COMPLETED`).

#### B. Daily Dual-Workload Time Series (`synthea_daily_workload.csv`)
- **Length:** 2,421 consecutive days (zero gaps).
- **Zero-Workload Days:** 14.8% (non-clinic weekends/holidays).
- **Columns:**
  - `window_start_time`: ISO UTC timestamp for the daily window.
  - `backup_workload_mb`: Daily cloud backup payload volume (target for backup LSTM).
  - `access_workload_mb`: Daily EHR retrieval and access volume (target for access LSTM).
  - `emergency_event_count`: Number of emergency clinical events during the day.
  - `total_event_count`: Total clinical operations during the day.

#### C. Hourly Dual-Workload Time Series (`synthea_hourly_workload.csv`)
- **Length:** 58,081 hourly windows.
- **Zero-Workload Windows:** 87.6%. Documented to demonstrate why daily aggregation was selected for stable machine learning forecasting.

---

## Historical Archive (`archive/legacy_custom_model/`)

Previous exploratory artifacts from the legacy custom-generated backup dataset (`hospital_backup_raw_data.csv`, `workload_timeseries_1h.csv`) have been quarantined to `archive/legacy_custom_model/`. They are strictly excluded from all final training, validation, evaluation, and inference paths.
