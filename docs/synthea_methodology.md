# Synthea EHR Workload Methodology Documentation

**Project:** AI-Driven Predictive and Emergency-Aware EHR Storage & Retrieval System  
**Dataset Source:** MITRE Synthea™ Public Synthetic Patient Population Simulator (CSV Export)

---

## 1. Academic Grounding & Data Lineage

The system uses the official Synthea public healthcare dataset as its sole underlying clinical data source. To maintain research integrity, source-derived clinical facts are explicitly distinguished from simulated cloud storage and access behaviors.

```
┌────────────────────────────────────────────────────────┐
│             Official Synthea Clinical Tables           │
│  - patients.csv (Demographics & master IDs)            │
│  - encounters.csv (Admissions, emergency, ambulatory)  │
│  - observations.csv (Vitals, lab measurements)         │
│  - procedures.csv (Surgeries, interventions)           │
│  - medications.csv (Prescriptions, dispensations)      │
│  - imaging_studies.csv (Radiology DICOM studies)       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           Synthea EHR Transformation Pipeline          │
│   src/ml_model/synthetic_ehr/ehr_transformer.py        │
└──────────────────────────┬─────────────────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│    Source-Derived Fields     │ │   Simulated Storage Fields   │
│ - timestamp                  │ │ - access_type (Read/Write)   │
│ - patient_id (Synthetic UUID)│ │ - data_size_mb (Type Sizing) │
│ - record_type                │ │ - storage_tier (Hot/Warm/Cold)│
│ - department                 │ │ - backup_status (Pending/Done│
│ - emergency_flag (ER Visits) │ │ - access_frequency (Causal)  │
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## 2. Field Classification: Source-Derived vs. Simulated

| Field Name | Category | Exact Derivation / Modeling Rule |
| :--- | :--- | :--- |
| `event_id` | **Synthea-Derived** | Unique deterministically generated identifier (`EHR_<index>_<hash>`). |
| `timestamp` | **Source-Derived** | Exact UTC clinical event timestamp from Synthea (`START` or `DATE`). |
| `patient_id` | **Source-Derived** | Synthea patient UUID (`PATIENT`). 100% synthetic; zero real PHI. |
| `record_type` | **Source-Derived** | Categorized from source table: `ENCOUNTER`, `OBSERVATION`, `PROCEDURE`, `MEDICATION`, `IMAGING_STUDY`. |
| `department` | **Mapped Source** | Deterministic mapping from clinical modality and encounter class: `LAB` (observations), `ER` (emergency/urgentcare), `SURG` (procedures), `OPD` (outpatient/wellness), `ICU` (inpatient), `RAD` (imaging studies), `GEN`. |
| `emergency_flag` | **Source-Derived** | `1` if child event belongs to an emergency/urgent admission (`ENCOUNTERCLASS in ['emergency', 'urgentcare']`); `0` otherwise. |
| `access_frequency`| **Causal Derived**| Strictly backward-looking count of prior events for the same patient in the preceding 30 days: `[T - 30 days, T)`. Current and future events are strictly excluded. |
| `access_type` | **Simulated** | Modeled based on clinical workflow: `WRITE` (new documentation), `UPDATE` (medication adjust), `READ` / `QUERY_BATCH` (chart & image review), `EMERGENCY_OVERRIDE` (acute trauma). |
| `data_size_mb` | **Simulated** | Parametric distribution based on medical imaging and EMR payload standards: Imaging (10–150 MB), Procedures (0.5–15 MB), Encounters (0.5–8 MB), Observations (0.05–1 MB), Medications (0.02–0.5 MB). |
| `criticality` | **Derived / Policy** | Deterministic clinical priority: `CRITICAL` (emergency episodes), `HIGH` (inpatient & imaging), `MEDIUM` (procedures & urgentcare), `LOW` (routine wellness). |
| `storage_tier` | **Simulated** | Cloud lifecycle policy: `HOT` (active encounter or $\le 14$ days old), `WARM` ($\le 90$ days), `COLD` ($\le 365$ days), `ARCHIVE` ($> 365$ days). |
| `backup_status` | **Simulated** | `PENDING` (new writes and updates requiring cloud replication) vs `COMPLETED` (historical reads). |

---

## 3. Workload Decoupling & Aggregation

To avoid conflating retrieval demand with backup storage demand, the time series are decoupled into two distinct targets:
1. **`access_workload_mb` (Retrieval / Read Demand):** Sum of all accessed EHR payloads in each time window, reflecting network retrieval and cache pressure.
2. **`backup_workload_mb` (Cloud Backup Storage Demand):** Sum of `data_size_mb` for events with `backup_status == 'PENDING'`, reflecting cloud storage replication volume.

### Temporal Density Analysis
* **Daily Workload:** 2,421 consecutive days (2020–2026). Zero-workload days: **14.8%** (mostly weekends). Selected for stable, robust forecasting.
* **Hourly Workload:** 58,081 hourly windows. Zero-workload hours: **87.6%**. Documented to explain sparsity limitations in single-facility cohorts.

---

## 4. Modeling & Baseline Evaluation Protocol

* **Holdout Split:** Chronological 70% Train (1,694 days), 15% Validation (363 days), 15% Holdout Test (364 days). No shuffle, zero data leakage.
* **Scalers:** `SyntheaWorkloadScaler` fitted strictly on the training partition.
* **Models Trained from Scratch:**
  - `best_synthea_backup_lstm.keras` for `backup_workload_mb`.
  - `best_synthea_access_lstm.keras` for `access_workload_mb`.
* **Baselines (Evaluated on Identical Test Observations):**
  - **Naive Persistence Baseline:** $\hat{y}_t = y_{t-1}$.
  - **7-Day Moving Average Baseline:** $\hat{y}_t = \frac{1}{7}\sum_{k=1}^7 y_{t-k}$.
* **Evaluation Metrics:**
  - **MAE (Mean Absolute Error, MB):** Primary scale-dependent accuracy metric.
  - **RMSE (Root Mean Squared Error, MB):** Sensitive to large workload spikes.
  - **WAPE (Weighted Absolute Percentage Error, %):** $\frac{\sum |y - \hat{y}|}{\sum y} \times 100$. Well-behaved with intermittent zero days.
  - **Filtered MAPE (%):** Calculated on $y_{\text{true}} > 1.0\text{ MB}$ to avoid division-by-zero distortion.
