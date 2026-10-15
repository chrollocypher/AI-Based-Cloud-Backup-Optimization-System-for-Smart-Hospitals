import os
import json
import pytest
from scripts.run_comparative_evaluation import generate_workload_trace, evaluate_policies, main as run_benchmark


def test_workload_trace_generation_reproducibility():
    """Verify trace generation is deterministic and reproducible under identical seed."""
    trace1 = generate_workload_trace(num_records=50, trace_hours=24, seed=123)
    trace2 = generate_workload_trace(num_records=50, trace_hours=24, seed=123)

    assert len(trace1["records"]) == len(trace2["records"])
    assert len(trace1["events"]) == len(trace2["events"])
    assert trace1["records"][0]["record_id"] == trace2["records"][0]["record_id"]


def test_comparative_evaluation_seven_metrics():
    """Verify evaluation outputs all 7 metrics across Policy A, B, and C."""
    trace = generate_workload_trace(num_records=60, trace_hours=24, seed=42)
    results = evaluate_policies(trace)

    assert "policy_comparison" in results
    p = results["policy_comparison"]

    pa = p["Policy_A_Proposed"]
    pb = p["Policy_B_Static"]
    pc = p["Policy_C_Conventional"]

    # 1. Cost savings: Policy A must show significant savings vs static baseline
    assert pa["cost_savings_vs_static_pct"] > 0
    assert pa["monthly_storage_cost_usd"] < pb["monthly_storage_cost_usd"]

    # 2. Safety & SLA adherence: Policy A must have higher critical availability than Policy C
    assert pa["critical_availability_pct"] > pc["critical_availability_pct"]
    assert pa["emergency_sla_violations"] < pc["emergency_sla_violations"]

    # 3. Cache Hit Rate: Policy A has non-zero edge cache hit rate
    assert pa["cache_hit_rate_pct"] > 0
    assert pb["cache_hit_rate_pct"] == 0

    # 4. Backup success rate
    assert pa["backup_success_rate_pct"] == 100.0


def test_benchmark_runner_artifact_generation():
    """Verify that running the benchmark generates the required summary artifacts."""
    results = run_benchmark()
    assert "workload_summary" in results

    results_dir = os.path.join(os.path.dirname(__file__), "../../../results")
    assert os.path.exists(os.path.join(results_dir, "comparative_evaluation_summary.json"))
    assert os.path.exists(os.path.join(results_dir, "comparative_metrics_table.csv"))
    assert os.path.exists(os.path.join(results_dir, "comparative_evaluation_report.md"))
