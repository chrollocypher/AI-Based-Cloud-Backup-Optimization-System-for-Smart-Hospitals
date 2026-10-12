"""
Synthetic EHR Transformation Module.
Extracts clinical events from Synthea CSVs (encounters, observations, procedures,
medications, imaging studies) and transforms them into an EHR access-log dataset
with 12 explicit fields, clearly separating source-derived data from simulated storage fields.

Boundary and Causal Rules:
- Events are sorted chronologically by timestamp.
- For each event at timestamp T for patient P, `access_frequency` counts strictly prior
  events for the same patient in the preceding 30 days: [T - 30 days, T).
- Current and future events are strictly excluded (zero lookahead leakage).
- Events occurring exactly at T - 30 days are included; events at T or later are excluded.
"""

import os
import uuid
import numpy as np
import pandas as pd
from datetime import datetime

# Reproducibility seed
SEED = 42
np.random.seed(SEED)

# Sizing parameters (MB) grounded by medical record type
SIZE_DISTRIBUTIONS = {
    'IMAGING': {'mean': 45.0, 'std': 15.0, 'min': 10.0, 'max': 150.0},
    'PROCEDURE': {'mean': 4.0, 'std': 1.5, 'min': 0.5, 'max': 15.0},
    'OBSERVATION': {'mean': 0.2, 'std': 0.1, 'min': 0.05, 'max': 1.0},
    'MEDICATION': {'mean': 0.1, 'std': 0.05, 'min': 0.02, 'max': 0.5},
    'ENCOUNTER': {'mean': 2.5, 'std': 1.0, 'min': 0.5, 'max': 8.0}
}

def get_department(record_type: str, encounter_class: str, modality: str = None) -> str:
    """Map Synthea clinical context deterministically to hospital department."""
    if record_type == 'IMAGING':
        return 'RAD'
    if encounter_class in ['emergency', 'urgentcare']:
        return 'ER'
    if encounter_class == 'inpatient':
        return 'ICU'
    if record_type == 'OBSERVATION':
        return 'LAB'
    if record_type == 'PROCEDURE':
        return 'SURG'
    if encounter_class in ['ambulatory', 'wellness', 'outpatient']:
        return 'OPD'
    return 'GEN'

def get_criticality(encounter_class: str, record_type: str, emergency_flag: int) -> str:
    """Assign deterministic clinical criticality."""
    if emergency_flag == 1 or encounter_class == 'emergency':
        return 'CRITICAL'
    if encounter_class == 'inpatient' or record_type == 'IMAGING':
        return 'HIGH'
    if encounter_class in ['urgentcare', 'ambulatory'] or record_type == 'PROCEDURE':
        return 'MEDIUM'
    return 'LOW'

def get_storage_tier(timestamp: pd.Timestamp, now_ref: pd.Timestamp, criticality: str) -> str:
    """Assign cloud storage tier based on recency and criticality."""
    age_days = (now_ref - timestamp).total_seconds() / 86400.0
    if criticality == 'CRITICAL' or age_days <= 14:
        return 'HOT'
    elif age_days <= 90:
        return 'WARM'
    elif age_days <= 365:
        return 'COLD'
    else:
        return 'ARCHIVE'

def compute_prior_30d_frequency(df: pd.DataFrame) -> np.ndarray:
    """
    Computes access_frequency for each event using only prior events for the same patient
    within the preceding 30 days: [T - 30 days, T).
    Strictly excludes current event and any future events.
    Boundary condition:
      - Window start (T - 30 days): inclusive.
      - Window end (T): exclusive (strictly prior timestamps).
    """
    frequencies = np.zeros(len(df), dtype=int)
    ns_30d = np.timedelta64(30, 'D')

    # Process grouped by patient
    for _, group in df.groupby('patient_id', sort=False):
        indices = group.index.values
        times = group['timestamp_dt'].values
        # times is monotonically increasing because df is sorted by timestamp_dt
        # Left bound: first index where timestamp >= times[i] - 30 days
        left_bounds = np.searchsorted(times, times - ns_30d, side='left')
        # Right bound: first index where timestamp == times[i] (strictly prior)
        curr_lefts = np.searchsorted(times, times, side='left')
        patient_counts = curr_lefts - left_bounds
        frequencies[indices] = patient_counts

    return frequencies

def transform_synthea_to_ehr_logs(
    synthea_dir: str,
    output_csv_path: str,
    start_year: int = 2020
) -> pd.DataFrame:
    """
    Ingests Synthea CSV tables and derives standard EHR access logs.
    """
    np.random.seed(SEED)
    print(f"Reading Synthea CSVs from: {synthea_dir}")
    enc_path = os.path.join(synthea_dir, 'encounters.csv')
    obs_path = os.path.join(synthea_dir, 'observations.csv')
    proc_path = os.path.join(synthea_dir, 'procedures.csv')
    med_path = os.path.join(synthea_dir, 'medications.csv')
    img_path = os.path.join(synthea_dir, 'imaging_studies.csv')

    df_enc = pd.read_csv(enc_path)
    df_obs = pd.read_csv(obs_path)
    df_proc = pd.read_csv(proc_path)
    df_med = pd.read_csv(med_path)
    df_img = pd.read_csv(img_path)

    # Encounter lookup map
    enc_lookup = df_enc.set_index('Id').to_dict('index')

    events = []

    # 1. Transform Encounters
    for _, row in df_enc.iterrows():
        ts_str = row['START']
        e_class = str(row['ENCOUNTERCLASS']).lower() if pd.notnull(row['ENCOUNTERCLASS']) else 'ambulatory'
        is_emerg = 1 if e_class in ['emergency', 'urgentcare'] else 0
        crit = get_criticality(e_class, 'ENCOUNTER', is_emerg)
        dept = get_department('ENCOUNTER', e_class)
        size = float(np.clip(
            np.random.normal(SIZE_DISTRIBUTIONS['ENCOUNTER']['mean'], SIZE_DISTRIBUTIONS['ENCOUNTER']['std']),
            SIZE_DISTRIBUTIONS['ENCOUNTER']['min'], SIZE_DISTRIBUTIONS['ENCOUNTER']['max']
        ))

        events.append({
            'source_record_id': str(row['Id']),
            'timestamp': ts_str,
            'patient_id': str(row['PATIENT']),
            'record_type': 'ENCOUNTER',
            'department': dept,
            'access_type': 'EMERGENCY_OVERRIDE' if is_emerg else 'WRITE',
            'data_size_mb': round(size, 3),
            'criticality': crit,
            'emergency_flag': is_emerg,
            'backup_status': 'PENDING'
        })

    # 2. Transform Observations
    for _, row in df_obs.iterrows():
        ts_str = row['DATE']
        enc_id = row['ENCOUNTER'] if pd.notnull(row['ENCOUNTER']) else None
        enc_info = enc_lookup.get(enc_id, {})
        e_class = str(enc_info.get('ENCOUNTERCLASS', 'outpatient')).lower()
        is_emerg = 1 if e_class in ['emergency', 'urgentcare'] else 0
        crit = get_criticality(e_class, 'OBSERVATION', is_emerg)
        dept = get_department('OBSERVATION', e_class)
        size = float(np.clip(
            np.random.normal(SIZE_DISTRIBUTIONS['OBSERVATION']['mean'], SIZE_DISTRIBUTIONS['OBSERVATION']['std']),
            SIZE_DISTRIBUTIONS['OBSERVATION']['min'], SIZE_DISTRIBUTIONS['OBSERVATION']['max']
        ))

        events.append({
            'source_record_id': f"OBS_{row.name}",
            'timestamp': ts_str,
            'patient_id': str(row['PATIENT']),
            'record_type': 'OBSERVATION',
            'department': dept,
            'access_type': 'WRITE' if np.random.rand() > 0.3 else 'READ',
            'data_size_mb': round(size, 3),
            'criticality': crit,
            'emergency_flag': is_emerg,
            'backup_status': 'PENDING' if np.random.rand() > 0.4 else 'COMPLETED'
        })

    # 3. Transform Procedures
    for _, row in df_proc.iterrows():
        ts_str = row['START']
        enc_id = row['ENCOUNTER'] if pd.notnull(row['ENCOUNTER']) else None
        enc_info = enc_lookup.get(enc_id, {})
        e_class = str(enc_info.get('ENCOUNTERCLASS', 'ambulatory')).lower()
        is_emerg = 1 if e_class in ['emergency', 'urgentcare'] else 0
        crit = get_criticality(e_class, 'PROCEDURE', is_emerg)
        dept = get_department('PROCEDURE', e_class)
        size = float(np.clip(
            np.random.normal(SIZE_DISTRIBUTIONS['PROCEDURE']['mean'], SIZE_DISTRIBUTIONS['PROCEDURE']['std']),
            SIZE_DISTRIBUTIONS['PROCEDURE']['min'], SIZE_DISTRIBUTIONS['PROCEDURE']['max']
        ))

        events.append({
            'source_record_id': f"PROC_{row.name}",
            'timestamp': ts_str,
            'patient_id': str(row['PATIENT']),
            'record_type': 'PROCEDURE',
            'department': dept,
            'access_type': 'WRITE',
            'data_size_mb': round(size, 3),
            'criticality': crit,
            'emergency_flag': is_emerg,
            'backup_status': 'PENDING'
        })

    # 4. Transform Medications
    for _, row in df_med.iterrows():
        ts_str = row['START']
        enc_id = row['ENCOUNTER'] if pd.notnull(row['ENCOUNTER']) else None
        enc_info = enc_lookup.get(enc_id, {})
        e_class = str(enc_info.get('ENCOUNTERCLASS', 'ambulatory')).lower()
        is_emerg = 1 if e_class in ['emergency', 'urgentcare'] else 0
        crit = get_criticality(e_class, 'MEDICATION', is_emerg)
        dept = get_department('MEDICATION', e_class)
        size = float(np.clip(
            np.random.normal(SIZE_DISTRIBUTIONS['MEDICATION']['mean'], SIZE_DISTRIBUTIONS['MEDICATION']['std']),
            SIZE_DISTRIBUTIONS['MEDICATION']['min'], SIZE_DISTRIBUTIONS['MEDICATION']['max']
        ))

        events.append({
            'source_record_id': f"MED_{row.name}",
            'timestamp': ts_str,
            'patient_id': str(row['PATIENT']),
            'record_type': 'MEDICATION',
            'department': dept,
            'access_type': 'UPDATE',
            'data_size_mb': round(size, 3),
            'criticality': crit,
            'emergency_flag': is_emerg,
            'backup_status': 'PENDING'
        })

    # 5. Transform Imaging Studies
    for _, row in df_img.iterrows():
        ts_str = row['DATE']
        enc_id = row['ENCOUNTER'] if pd.notnull(row['ENCOUNTER']) else None
        enc_info = enc_lookup.get(enc_id, {})
        e_class = str(enc_info.get('ENCOUNTERCLASS', 'outpatient')).lower()
        is_emerg = 1 if e_class in ['emergency', 'urgentcare'] else 0
        crit = get_criticality(e_class, 'IMAGING', is_emerg)
        modality = str(row['MODALITY_DESCRIPTION']) if pd.notnull(row['MODALITY_DESCRIPTION']) else 'DX'
        dept = get_department('IMAGING', e_class, modality)
        size = float(np.clip(
            np.random.normal(SIZE_DISTRIBUTIONS['IMAGING']['mean'], SIZE_DISTRIBUTIONS['IMAGING']['std']),
            SIZE_DISTRIBUTIONS['IMAGING']['min'], SIZE_DISTRIBUTIONS['IMAGING']['max']
        ))

        events.append({
            'source_record_id': str(row['Id']),
            'timestamp': ts_str,
            'patient_id': str(row['PATIENT']),
            'record_type': 'IMAGING_STUDY',
            'department': dept,
            'access_type': 'QUERY_BATCH' if np.random.rand() > 0.5 else 'WRITE',
            'data_size_mb': round(size, 3),
            'criticality': crit,
            'emergency_flag': is_emerg,
            'backup_status': 'PENDING'
        })

    df_out = pd.DataFrame(events)
    df_out['timestamp_dt'] = pd.to_datetime(df_out['timestamp'], utc=True)
    # Strictly sort chronologically
    df_out = df_out.sort_values('timestamp_dt').reset_index(drop=True)

    # Compute strictly causal prior 30-day access_frequency BEFORE any cutoff filtering
    # to maintain true longitudinal patient history
    df_out['access_frequency'] = compute_prior_30d_frequency(df_out)

    # Filter to start_year onwards for dense modern period
    if start_year:
        cutoff = pd.Timestamp(f"{start_year}-01-01T00:00:00Z")
        df_out = df_out[df_out['timestamp_dt'] >= cutoff].reset_index(drop=True)

    # Storage Tier assignment based on recency and criticality
    now_ref = df_out['timestamp_dt'].max()
    df_out['storage_tier'] = df_out.apply(
        lambda r: get_storage_tier(r['timestamp_dt'], now_ref, r['criticality']),
        axis=1
    )

    # Assign deterministic reproducible event_id
    df_out['event_id'] = [f"EHR_{i:06d}_{uuid.UUID(int=i + SEED).hex[:8]}" for i in range(len(df_out))]

    # Standardize column order (all 12 required fields)
    columns_order = [
        'event_id',
        'timestamp',
        'patient_id',
        'record_type',
        'department',
        'access_type',
        'access_frequency',
        'data_size_mb',
        'criticality',
        'storage_tier',
        'emergency_flag',
        'backup_status'
    ]
    df_final = df_out[columns_order]

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    df_final.to_csv(output_csv_path, index=False)
    print(f"Transformed {len(df_final)} records successfully saved to {output_csv_path}")

    return df_final

if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    synthea_input = os.path.join(base_dir, 'dataset', 'synthea')
    output_file = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_ehr_access_logs.csv')
    transform_synthea_to_ehr_logs(synthea_input, output_file, start_year=2020)
