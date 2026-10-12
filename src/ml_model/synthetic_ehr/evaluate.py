"""
Evaluation module comparing the Synthea LSTM models against
Naive and Moving Average baselines on the holdout test set for both
backup_workload_mb and access_workload_mb.
Calculates MAE, RMSE, MAPE (with documented y_true > 1.0 MB filter), and WAPE.
Reports which model wins each metric without overstating superiority.

Supports optional row-level prediction export to results/synthea_test_predictions.csv
via `--export-predictions` CLI flag.
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.ml_model.synthetic_ehr.data_loader import (
    load_and_split_synthea_workload,
    SyntheaWorkloadScaler,
    create_workload_sequences
)

def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calculates MAE, RMSE, filtered MAPE (y_true > 1.0 MB), and WAPE.
    - WAPE = (sum(|y_true - y_pred|) / sum(y_true)) * 100
    """
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # WAPE (Weighted Absolute Percentage Error) - mathematically stable with intermittent zeros
    sum_true = float(np.sum(y_true))
    wape = float((np.sum(np.abs(y_true - y_pred)) / sum_true) * 100.0) if sum_true > 0 else 0.0

    # Filtered MAPE (only on actual values > 1.0 MB to avoid zero explosion)
    mask = y_true > 1.0
    if np.sum(mask) > 0:
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)
    else:
        mape = 0.0

    return {
        'MAE_mb': round(mae, 2),
        'RMSE_mb': round(rmse, 2),
        'WAPE_pct': round(wape, 2),
        'MAPE_filtered_pct': round(mape, 2)
    }

def evaluate_single_target(
    workload_csv: str,
    target_column: str,
    model_path: str,
    scaler_path: str,
    lookback: int = 14
) -> dict:
    """
    Evaluates LSTM and baselines on identical holdout test observations for a given target.
    Returns metrics dict along with test timestamps and predicted arrays.
    """
    print(f"\n=======================================================")
    print(f"Evaluating Target: {target_column}")
    print(f"=======================================================")

    train_raw, val_raw, test_raw, full_df = load_and_split_synthea_workload(
        workload_csv,
        target_column=target_column,
        lookback=lookback
    )

    n = len(full_df)
    val_end = int(n * (0.70 + 0.15))
    target_dates = full_df['window_start_time'].iloc[val_end:].dt.strftime('%Y-%m-%dT%H:%M:%SZ').values

    scaler = SyntheaWorkloadScaler()
    scaler.load(scaler_path)

    # Prepare ground truth targets
    _, y_test_raw = create_workload_sequences(test_raw, lookback)
    y_test_true = y_test_raw.flatten()

    # 1. LSTM Predictions
    model = tf.keras.models.load_model(model_path)
    test_scaled = scaler.transform(test_raw)
    X_test, _ = create_workload_sequences(test_scaled, lookback)
    preds_scaled = model.predict(X_test, verbose=0)
    preds_mb = scaler.inverse_transform(preds_scaled).flatten()
    lstm_preds = np.clip(preds_mb, 0.0, None)

    lstm_metrics = compute_all_metrics(y_test_true, lstm_preds)

    # 2. Naive Baseline (Persistence: last observed value in lookback window)
    naive_preds = test_raw[lookback - 1 : -1].flatten()
    naive_metrics = compute_all_metrics(y_test_true, naive_preds)

    # 3. 7-Day Moving Average Baseline
    ma_preds = []
    for i in range(len(test_raw) - lookback):
        window = test_raw[i : i + lookback].flatten()
        ma_preds.append(np.mean(window[-7:]))
    ma_preds = np.array(ma_preds)
    ma_metrics = compute_all_metrics(y_test_true, ma_preds)

    models_dict = {
        'LSTM': lstm_metrics,
        'Baseline_Naive_Persistence': naive_metrics,
        'Baseline_7Day_Moving_Average': ma_metrics
    }

    # Determine metric winners
    winners = {}
    for metric in ['MAE_mb', 'RMSE_mb', 'WAPE_pct', 'MAPE_filtered_pct']:
        best_model = min(models_dict.keys(), key=lambda m: models_dict[m][metric])
        winners[metric] = {
            'best_model': best_model,
            'best_value': models_dict[best_model][metric]
        }

    print(f"{'Model':<30} | {'MAE (MB)':<10} | {'RMSE (MB)':<10} | {'WAPE (%)':<10} | {'MAPE (>1MB)':<12}")
    print("-" * 80)
    for name, m in models_dict.items():
        print(f"{name:<30} | {m['MAE_mb']:<10.2f} | {m['RMSE_mb']:<10.2f} | {m['WAPE_pct']:<10.2f} | {m['MAPE_filtered_pct']:<12.2f}")

    print("\nMetric Winners:")
    for k, v in winners.items():
        print(f"  - {k:<20}: {v['best_model']} ({v['best_value']})")

    return {
        'test_samples': len(y_test_true),
        'lookback_days': lookback,
        'models': models_dict,
        'winners': winners,
        'predictions_data': {
            'window_start_time': target_dates,
            'target_name': target_column,
            'actual_workload_mb': y_test_true,
            'predicted_lstm_mb': np.round(lstm_preds, 2),
            'predicted_naive_mb': np.round(naive_preds, 2),
            'predicted_moving_average_mb': np.round(ma_preds, 2)
        }
    }

def run_full_evaluation(export_predictions: bool = False, predictions_output_path: str = None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    data_csv = os.path.join(base_dir, 'dataset', 'synthea', 'processed', 'synthea_daily_workload.csv')
    models_dir = os.path.join(base_dir, 'src', 'ml_model', 'synthetic_ehr', 'models')
    out_json = os.path.join(base_dir, 'results', 'synthea_evaluation_metrics.json')

    results = {}

    # 1. Evaluate Backup Workload
    eval_backup = evaluate_single_target(
        workload_csv=data_csv,
        target_column='backup_workload_mb',
        model_path=os.path.join(models_dir, 'best_synthea_backup_lstm.keras'),
        scaler_path=os.path.join(models_dir, 'synthea_backup_scaler.json')
    )

    # 2. Evaluate Access Workload
    eval_access = evaluate_single_target(
        workload_csv=data_csv,
        target_column='access_workload_mb',
        model_path=os.path.join(models_dir, 'best_synthea_access_lstm.keras'),
        scaler_path=os.path.join(models_dir, 'synthea_access_scaler.json')
    )

    results['backup_workload'] = {
        'test_samples': eval_backup['test_samples'],
        'lookback_days': eval_backup['lookback_days'],
        'models': eval_backup['models'],
        'winners': eval_backup['winners']
    }

    results['access_workload'] = {
        'test_samples': eval_access['test_samples'],
        'lookback_days': eval_access['lookback_days'],
        'models': eval_access['models'],
        'winners': eval_access['winners']
    }

    # Verify existing JSON integrity before saving
    if os.path.exists(out_json):
        with open(out_json, 'r') as f:
            existing_metrics = json.load(f)
        for target_key in ['backup_workload', 'access_workload']:
            for model_name in existing_metrics[target_key]['models']:
                for metric_key in ['MAE_mb', 'RMSE_mb', 'WAPE_pct', 'MAPE_filtered_pct']:
                    calc_val = results[target_key]['models'][model_name][metric_key]
                    exist_val = existing_metrics[target_key]['models'][model_name][metric_key]
                    if calc_val != exist_val:
                        raise ValueError(f"Discrepancy detected for {target_key} {model_name} {metric_key}: {calc_val} != {exist_val}")

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nComprehensive metrics verified and saved to: {out_json}")

    # Optional Prediction Export
    if export_predictions:
        if predictions_output_path is None:
            predictions_output_path = os.path.join(base_dir, 'results', 'synthea_test_predictions.csv')

        df_backup = pd.DataFrame(eval_backup['predictions_data'])
        df_access = pd.DataFrame(eval_access['predictions_data'])
        df_combined = pd.concat([df_backup, df_access], ignore_index=True)

        os.makedirs(os.path.dirname(predictions_output_path), exist_ok=True)
        df_combined.to_csv(predictions_output_path, index=False)
        print(f"\nRow-level predictions successfully exported to: {predictions_output_path} ({len(df_combined)} rows)")

    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate Synthea LSTM models against baselines.")
    parser.add_argument(
        '--export-predictions',
        action='store_true',
        help="Export row-level test predictions to results/synthea_test_predictions.csv"
    )
    parser.add_argument(
        '--output-path',
        type=str,
        default=None,
        help="Custom file path for exported predictions CSV"
    )
    args = parser.parse_args()

    run_full_evaluation(
        export_predictions=args.export_predictions,
        predictions_output_path=args.output_path
    )
