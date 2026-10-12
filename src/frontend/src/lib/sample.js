// Mirrors src/backend/scripts/seed_data.py so an empty backend can be populated from the UI.
export const SAMPLE_RECORDS = [
  { record_id: 'EHR_10025', record_type: 'Emergency EHR', department: 'Emergency', data_size_mb: 25.4, access_frequency: 18 },
  { record_id: 'CT_20041', record_type: 'CT', department: 'Radiology', data_size_mb: 450.0, access_frequency: 12 },
  { record_id: 'MRI_20231', record_type: 'MRI', department: 'Neurology', data_size_mb: 780.5, access_frequency: 8 },
  { record_id: 'MON_30089', record_type: 'Monitoring', department: 'ICU', data_size_mb: 15.2, access_frequency: 42 },
  { record_id: 'ADMIN_9812', record_type: 'Administrative', department: 'Billing', data_size_mb: 5.8, access_frequency: 2 },
  { record_id: 'SURG_40012', record_type: 'Surgical', department: 'Operation Theatre', data_size_mb: 310.0, access_frequency: 15 },
];

// Record types and departments the backend's criticality rules recognise.
export const RECORD_TYPES = ['Emergency EHR', 'EHR', 'ICU', 'CT', 'MRI', 'Surgical', 'Monitoring', 'Outpatient', 'Administrative', 'Billing'];
export const DEPARTMENTS = ['Emergency', 'ICU', 'Radiology', 'Neurology', 'Operation Theatre', 'Cardiology', 'Outpatient', 'Billing'];
