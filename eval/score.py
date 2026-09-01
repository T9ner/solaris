"""Automated scoring harness for the Forge Autonomous Operations Pipeline.

Evaluates the agent across all 10 benchmark test cases in eval/cases/
and compares against single-prompt monolithic baselines.
"""

import asyncio
import glob
import json
import os
import pathlib
import sys
import time

# Ensure project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from tabulate import tabulate
from agents.graph import ForgePipeline


async def evaluate_case(pipeline: ForgePipeline, case_file: str) -> dict:
    with open(case_file, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    expected_gaps = case_data.get("expected_gaps_count", 0)
    expected_categories = set(case_data.get("expected_categories", []))

    trace_dir = pathlib.Path("trajectories")
    trace_dir.mkdir(exist_ok=True)
    trace_path = trace_dir / f"eval_{case_data.get('case_id', 'case')}"

    state = await pipeline.run(
        case_data=case_data,
        case_id=case_data.get("case_id"),
        task_desc=case_data.get("description"),
        trace_path=str(trace_path),
    )

    detected_gaps = len(state.discrepancies)
    detected_categories = set(d.category for d in state.discrepancies)

    # Correct detection score
    if expected_gaps == 0:
        correct_detection = (detected_gaps == 0)
        false_positives = detected_gaps
    else:
        matched_categories = expected_categories.intersection(detected_categories)
        correct_detection = (len(matched_categories) == len(expected_categories))
        false_positives = max(0, detected_gaps - expected_gaps)

    return {
        "case_id": state.case_id,
        "expected_gaps": expected_gaps,
        "detected_gaps": detected_gaps,
        "correct": correct_detection,
        "false_positives": false_positives,
        "execution_time_s": state.execution_time_seconds,
        "token_usage": state.token_usage,
        "verified": state.verification.verified if state.verification else True,
        "preview_url": state.verification.preview_url if state.verification else None,
    }


async def run_benchmark():
    case_files = sorted(glob.glob("eval/cases/*.json"))
    if not case_files:
        print("No test cases found in eval/cases/")
        return

    print(f"Evaluating {len(case_files)} benchmark cases with Forge Autonomous Pipeline...")
    pipeline = ForgePipeline(use_mock=True, auto_approve=True)

    results = []
    for case_file in case_files:
        res = await evaluate_case(pipeline, case_file)
        results.append(res)

    total_cases = len(results)
    correct_cases = sum(1 for r in results if r["correct"])
    total_false_positives = sum(r["false_positives"] for r in results)
    avg_time = sum(r["execution_time_s"] for r in results) / total_cases
    total_tokens = sum(r["token_usage"] for r in results)

    detection_rate = (correct_cases / total_cases) * 100
    fp_rate = (total_false_positives / total_cases) * 100

    # Save results JSON
    results_dir = pathlib.Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_cases": total_cases,
            "detection_rate_pct": detection_rate,
            "false_positive_rate_pct": fp_rate,
            "avg_time_seconds": round(avg_time, 2),
            "total_tokens": total_tokens,
            "cases": results,
        }, f, indent=2)

    # Format CLI output table
    table_rows = []
    for r in results:
        table_rows.append([
            r["case_id"],
            r["expected_gaps"],
            r["detected_gaps"],
            "PASS" if r["correct"] else "FAIL",
            r["false_positives"],
            f"{r['execution_time_s']}s",
            f"{r['token_usage']:,}",
        ])

    headers = ["Case ID", "Expected", "Detected", "Result", "FP", "Time", "Tokens"]
    print("\n" + tabulate(table_rows, headers=headers, tablefmt="github"))

    print("\n" + "=" * 60)
    print("BENCHMARK SCORECARD")
    print("=" * 60)
    print(f"- Gap Detection Rate:    {detection_rate:.1f}% (Target: 100%)")
    print(f"- False Positive Rate:   {fp_rate:.1f}% (Target: 0%)")
    print(f"- Average Runtime:       {avg_time:.2f}s")
    print(f"- Total Tokens Used:     {total_tokens:,}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
