# Legacy Custom Model Archive

This directory contains historical artifacts from the early exploratory phase of the project that used a custom self-generated backup dataset.

> [!WARNING]
> **DISALLOWED FROM FINAL EXPERIMENTS:**
> In accordance with the teacher's requirement, the project uses the official **Synthea public healthcare dataset** as the sole underlying data source for all final experiments and evaluations.
> The artifacts in this archive are preserved strictly for version control history and auditability.
> They are **strictly excluded** from all active training, validation, evaluation, and inference paths.

## Archived Artifacts

- `dataset/raw/hospital_backup_raw_data.csv`: Old custom synthetic generator output (~19.9 MB).
- `dataset/processed/workload_timeseries_1h.csv`: Old 1-hour univariate aggregation (~256 KB).
- `src/ml_model/generate_synthetic_data.py`: Script that produced the legacy custom dataset.
- `src/ml_model/models/`: Checkpoints (`best_lstm_model.keras`, `best_lstm.keras`) trained on the legacy custom dataset.
- `src/ml_model/lstm/`: Legacy training and prediction scripts (`model.py`, `train.py`, `predict.py`).
- `src/ml_model/preprocessing/`: Legacy preprocessor and pipeline scripts.
- `src/ml_model/baselines/`: Legacy baseline evaluators.
- `src/ml_model/pipeline/`: Early decision pipeline demo scripts.
- `src/ml_model/queue/lstm_queue_demo.py`: Demo script that referenced the legacy model checkpoint.

For the active, approved ML pipeline, refer to `src/ml_model/synthetic_ehr/` and `dataset/synthea/`.
