// Mirrors src/backend/scripts/seed_data.py so an empty backend can be populated from the UI.
export const SAMPLE_RECORDS = [
  { record_id: 'EHR_10025', patient_id: 'P_SYN_10482', record_type: 'Emergency EHR', department: 'Emergency', data_size_mb: 25.4, access_frequency: 18, storage_tier: 'STANDARD', emergency_flag: true },
  { record_id: 'CT_20041', patient_id: 'P_SYN_20391', record_type: 'CT', department: 'Radiology', data_size_mb: 450.0, access_frequency: 12, storage_tier: 'STANDARD', emergency_flag: false },
  { record_id: 'MRI_20231', patient_id: 'P_SYN_30912', record_type: 'MRI', department: 'Neurology', data_size_mb: 780.5, access_frequency: 8, storage_tier: 'STANDARD_IA', emergency_flag: false },
  { record_id: 'MON_30089', patient_id: 'P_SYN_40129', record_type: 'Monitoring', department: 'ICU', data_size_mb: 15.2, access_frequency: 42, storage_tier: 'STANDARD', emergency_flag: true },
  { record_id: 'ADMIN_9812', patient_id: 'P_SYN_50918', record_type: 'Administrative', department: 'Billing', data_size_mb: 5.8, access_frequency: 2, storage_tier: 'GLACIER', emergency_flag: false },
  { record_id: 'SURG_40012', patient_id: 'P_SYN_60192', record_type: 'Surgical', department: 'Operation Theatre', data_size_mb: 310.0, access_frequency: 15, storage_tier: 'STANDARD', emergency_flag: false },
];

export const TIER_LABELS = {
  STANDARD: 'HOT',
  STANDARD_IA: 'WARM',
  GLACIER: 'COLD',
  GLACIER_FLEXIBLE: 'COLD',
  DEEP_ARCHIVE: 'ARCHIVE',
  HOT: 'HOT',
  WARM: 'WARM',
  COLD: 'COLD',
  ARCHIVE: 'ARCHIVE',
};

// Record types and departments the backend's criticality rules recognise.
export const RECORD_TYPES = ['Emergency EHR', 'EHR', 'ICU', 'CT', 'MRI', 'Surgical', 'Monitoring', 'Outpatient', 'Administrative', 'Billing'];
export const DEPARTMENTS = ['Emergency', 'ICU', 'Radiology', 'Neurology', 'Operation Theatre', 'Cardiology', 'Outpatient', 'Billing'];
