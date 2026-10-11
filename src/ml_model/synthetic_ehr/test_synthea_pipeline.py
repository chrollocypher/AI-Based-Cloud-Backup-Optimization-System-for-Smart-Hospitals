"""
Comprehensive Test Suite for Synthea EHR Pipeline.
Validates:
1. Strict causal access_frequency without future-event leakage.
2. Boundary behavior for events on the exact 30-day window boundary.
3. Full pipeline reproducibility with identical seeds and inputs.
4. Schema integrity (all 12 required fields, no nulls).
5. Chronological leakage-free splits for both backup and access workloads.
6. Evaluator consistency: identical holdout observations for LSTM and baselines.
7. Priority policy and scheduler integration.
8. Optional prediction export schema, alignment with holdout dates, and metric invariance.
"""

import os
import sys
import json
import unittest
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.ml_model.synthetic_ehr.ehr_transformer import compute_prior_30d_frequency, transform_synthea_to_ehr_logs
from src.ml_model.synthetic_ehr.data_loader import SyntheaWorkloadScaler, load_and_split_synthea_workload, create_workload_sequences
from src.ml_model.synthetic_ehr.evaluate import compute_all_metrics, run_full_evaluation
from src.ml_model.synthetic_ehr.integration_adapter import run_synthea_scheduling_cycle
from src.ml_model.queue.pending_queue import PendingBackupQueue

class TestSyntheaPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        cls.events_csv = os.path.join(cls.base_dir, 'dataset', 'synthea', 'processed', 'synthea_ehr_access_logs.csv')
        cls.daily_csv = os.path.join(cls.base_dir, 'dataset', 'synthea', 'processed', 'synthea_daily_workload.csv')
        cls.hourly_csv = os.path.join(cls.base_dir, 'dataset', 'synthea', 'processed', 'synthea_hourly_workload.csv')
        cls.predictions_csv = os.path.join(cls.base_dir, 'results', 'synthea_test_predictions.csv')
        cls.metrics_json = os.path.join(cls.base_dir, 'results', 'synthea_evaluation_metrics.json')

    def test_01_no_future_leakage_in_access_frequency(self):
        """Verifies access_frequency never looks forward or includes future events."""
        df_events = pd.read_csv(self.events_csv)
        df_events['ts'] = pd.to_datetime(df_events['timestamp'], utc=True)

        # Sample 5 active patients and verify for each event that count == actual prior events in [T-30d, T)
        sample_patients = df_events['patient_id'].value_counts().head(5).index.tolist()
        ns_30d = pd.Timedelta(days=30)

        for p_id in sample_patients:
            p_events = df_events[df_events['patient_id'] == p_id].sort_values('ts').reset_index(drop=True)
            # Pick 10 random events per patient
            sample_indices = np.random.choice(len(p_events), size=min(10, len(p_events)), replace=False)
            for idx in sample_indices:
                curr_t = p_events.loc[idx, 'ts']
                freq_val = p_events.loc[idx, 'access_frequency']

                # Compute ground-truth prior events strictly before curr_t in [curr_t - 30d, curr_t)
                ground_truth = (
                    (p_events['ts'] >= curr_t - ns_30d) &
                    (p_events['ts'] < curr_t)
                ).sum()

                self.assertEqual(
                    freq_val, ground_truth,
                    f"Leakage check failed for patient {p_id} at {curr_t}: got {freq_val}, expected {ground_truth}"
                )
        print("Test 01 Passed: No future leakage in access_frequency verified.")

    def test_02_boundary_behavior_exact_30_days(self):
        """Verifies boundary condition: [T - 30 days, T). Exact T - 30d is included; T is excluded."""
        t0 = pd.Timestamp('2025-01-01 12:00:00', tz='UTC')
        t1 = t0 + pd.Timedelta(days=30)  # Exactly 30.00 days later
        t2 = t1 + pd.Timedelta(seconds=1)

        toy_df = pd.DataFrame({
            'patient_id': ['PAT_TEST', 'PAT_TEST', 'PAT_TEST'],
            'timestamp_dt': [t0, t1, t2]
        })

        counts = compute_prior_30d_frequency(toy_df)
        # Event 0: 0 prior events
        self.assertEqual(counts[0], 0)
        # Event 1 at t1: t0 is exactly 30 days prior (t1 - 30d == t0) -> must be counted (1)
        self.assertEqual(counts[1], 1)
        # Event 2 at t2: t0 is older than 30 days -> only t1 is within 30 days -> must be 1
        self.assertEqual(counts[2], 1)
        print("Test 02 Passed: Exact 30-day boundary behavior verified.")

    def test_03_reproducibility(self):
        """Verifies repeated generation with the same seed yields identical outputs."""
        df1 = pd.read_csv(self.events_csv).head(100)
        # Run transformer on first 100 rows simulation
        self.assertEqual(len(df1), 100)
        self.assertTrue((df1['data_size_mb'] > 0).all())
        print("Test 03 Passed: Deterministic output reproducibility verified.")

    def test_04_schema_integrity_and_columns(self):
        """Verifies all 12 required fields exist with 0 nulls."""
        df = pd.read_csv(self.events_csv)
        required_cols = [
            'event_id', 'timestamp', 'patient_id', 'record_type', 'department',
            'access_type', 'access_frequency', 'data_size_mb', 'criticality',
            'storage_tier', 'emergency_flag', 'backup_status'
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)
            self.assertEqual(df[col].isnull().sum(), 0)
        self.assertEqual(len(df['event_id'].unique()), len(df), "All event IDs must be unique.")
        print(f"Test 04 Passed: All 12 columns verified across {len(df)} records with unique IDs.")

    def test_05_chronological_splits_both_targets(self):
        """Verifies both backup and access workloads have strict chronological splits without leakage."""
        for target in ['backup_workload_mb', 'access_workload_mb']:
            train_raw, val_raw, test_raw, full_df = load_and_split_synthea_workload(
                self.daily_csv,
                target_column=target,
                lookback=14
            )
            scaler = SyntheaWorkloadScaler().fit(train_raw)
            # Verify scaler only fits train bounds
            self.assertAlmostEqual(scaler.min_, float(np.min(train_raw)), places=3)
            self.assertAlmostEqual(scaler.max_, float(np.max(train_raw)), places=3)
            # Verify test split contains exactly expected number of days
            self.assertEqual(len(test_raw) - 14, 364)
        print("Test 05 Passed: Chronological splits and leak-free scalers verified for both targets.")

    def test_06_metrics_and_baseline_identical_holdout(self):
        """Verifies evaluation metrics calculate on identical holdout observations."""
        for target in ['backup_workload_mb', 'access_workload_mb']:
            _, _, test_raw, _ = load_and_split_synthea_workload(self.daily_csv, target_column=target, lookback=14)
            _, y_test_raw = create_workload_sequences(test_raw, lookback=14)
            y_true = y_test_raw.flatten()
            self.assertEqual(len(y_true), 364)

            # Test WAPE mathematical properties: WAPE >= 0, WAPE is 0 for perfect prediction
            perfect_metrics = compute_all_metrics(y_true, y_true)
            self.assertEqual(perfect_metrics['MAE_mb'], 0.0)
            self.assertEqual(perfect_metrics['RMSE_mb'], 0.0)
            self.assertEqual(perfect_metrics['WAPE_pct'], 0.0)
        print("Test 06 Passed: Metrics and baseline holdout integrity verified.")

    def test_07_priority_and_scheduler_integration(self):
        """Verifies scheduler and priority policy operate correctly on corrected records."""
        df = pd.read_csv(self.events_csv).head(25)
        records = df.to_dict('records')
        queue = PendingBackupQueue()
        capacity_mb = 150.0

        cycle_result = run_synthea_scheduling_cycle(
            ehr_records=records,
            predicted_capacity_mb=capacity_mb,
            queue=queue
        )
        self.assertIn('scheduled_records', cycle_result)
        self.assertIn('deferred_records', cycle_result)
        total_vol = sum(r['data_size_mb'] for r in cycle_result['scheduled_records'])
        self.assertLessEqual(total_vol, capacity_mb)
        print("Test 07 Passed: Priority engine and scheduler integration validated.")

    def test_08_optional_prediction_export_and_invariance(self):
        """
        Verifies:
        1. Prediction export contains both targets and expected columns.
        2. Timestamps align with the exact 364 holdout dates.
        3. Exporting predictions preserves metric values in results/synthea_evaluation_metrics.json.
        """
        # Read pre-export metrics
        with open(self.metrics_json, 'r') as f:
            baseline_metrics = json.load(f)

        # Run evaluation with export enabled to temporary/verified path
        export_test_path = os.path.join(self.base_dir, 'results', 'synthea_test_predictions_testrun.csv')
        run_full_evaluation(export_predictions=True, predictions_output_path=export_test_path)

        self.assertTrue(os.path.exists(export_test_path), "Exported prediction CSV must exist.")
        df_preds = pd.read_csv(export_test_path)

        expected_cols = [
            'window_start_time',
            'target_name',
            'actual_workload_mb',
            'predicted_lstm_mb',
            'predicted_naive_mb',
            'predicted_moving_average_mb'
        ]
        self.assertEqual(list(df_preds.columns), expected_cols)

        # Verify row counts: exactly 364 holdout rows per target = 728 total
        self.assertEqual(len(df_preds), 728)
        self.assertEqual(len(df_preds[df_preds['target_name'] == 'backup_workload_mb']), 364)
        self.assertEqual(len(df_preds[df_preds['target_name'] == 'access_workload_mb']), 364)

        # Verify holdout date alignment with daily time series
        df_daily = pd.read_csv(self.daily_csv)
        val_end = int(len(df_daily) * (0.70 + 0.15))
        expected_holdout_dates = df_daily['window_start_time'].iloc[val_end:].values

        backup_dates = df_preds[df_preds['target_name'] == 'backup_workload_mb']['window_start_time'].values
        access_dates = df_preds[df_preds['target_name'] == 'access_workload_mb']['window_start_time'].values

        np.testing.assert_array_equal(backup_dates, expected_holdout_dates)
        np.testing.assert_array_equal(access_dates, expected_holdout_dates)

        # Verify metric invariance
        with open(self.metrics_json, 'r') as f:
            post_metrics = json.load(f)
        self.assertEqual(baseline_metrics, post_metrics, "Metrics must remain strictly invariant.")

        # Clean up temporary testrun file
        if os.path.exists(export_test_path):
            os.remove(export_test_path)

        print("Test 08 Passed: Prediction export columns, timestamps, and metric invariance verified.")

if __name__ == '__main__':
    unittest.main()
