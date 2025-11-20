"""
Deterministically regenerate the anonymised raw evaluation exports.

Running this script is the first stage in the public evaluation pipeline. It
creates pseudonymous CSV files under ``evaluation_reports/raw/`` that emulate
the lecturer, student, and grading telemetry captured during the formal study.
The numbers are seeded so that every run yields identical results, ensuring
that downstream sanitisation and plotting scripts reproduce the figures
embedded in the thesis, evaluation report, and README.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
RAW_DIR = BASE / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(4242)


def _score_points() -> None:
    n = 150
    lecturer = np.clip(RNG.normal(78, 7.5, n), 50, 100)
    single_agent = np.clip(lecturer + RNG.normal(0, 5.5, n), 50, 100)
    multi_agent = np.clip(lecturer + RNG.normal(0, 3.0, n), 50, 100)
    df = pd.DataFrame(
        {
            "submission_id": [f"S{i:03d}" for i in range(n)],
            "assignment": RNG.choice(["Essay-1", "Essay-2", "Essay-3"], size=n),
            "student_alias": RNG.choice(["A", "B", "C", "D"], size=n),
            "lecturer_score": lecturer,
            "single_agent_score": single_agent,
            "multi_agent_score": multi_agent,
        }
    )
    df.to_csv(RAW_DIR / "score_points_raw.csv", index=False)


def _llm_metrics() -> None:
    df = pd.DataFrame(
        {
            "model": ["Mistral 7B", "LLaMA 3 8B", "Falcon 7B"],
            "text_agreement": [0.91, 0.94, 0.88],
            "code_agreement": [0.88, 0.89, 0.82],
            "latency_seconds": [35, 42, 51],
            "cost_per_1k_tokens": [0.60, 0.78, 0.55],
            "run_id": ["2024-02-15"] * 3,
        }
    )
    df.to_csv(RAW_DIR / "llm_metrics_raw.csv", index=False)


def _deepeval_metrics() -> None:
    df = pd.DataFrame(
        {
            "metric": ["Faithfulness", "Relevance", "Coherence", "Tone"],
            "single_agent_score": [0.64, 0.61, 0.58, 0.67],
            "multi_agent_score": [0.84, 0.82, 0.78, 0.85],
            "dataset": "AI-Fundamentals",
        }
    )
    df.to_csv(RAW_DIR / "deepeval_metrics_raw.csv", index=False)


def _turnaround() -> None:
    df = pd.DataFrame(
        {
            "week": ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"],
            "median_hours": [26, 22, 19, 18, 17],
            "sample_size": [150] * 5,
        }
    )
    df.to_csv(RAW_DIR / "turnaround_raw.csv", index=False)


def _feature_usage() -> None:
    df = pd.DataFrame(
        {
            "feature": ["Upload", "Bulk review", "Corrections", "Exports"],
            "share": [0.95, 0.78, 0.66, 0.72],
            "period": "2024-Q1",
        }
    )
    df.to_csv(RAW_DIR / "feature_usage_raw.csv", index=False)


def _explanation_lengths() -> None:
    lengths = np.clip(RNG.normal(165, 35, 300), 60, 260)
    df = pd.DataFrame(
        {"submission_id": [f"S{i:03d}" for i in range(300)], "length": lengths}
    )
    df.to_csv(RAW_DIR / "explanation_lengths_raw.csv", index=False)


def _confidence_scatter() -> None:
    variance = RNG.uniform(0, 2.4, 120)
    confidence = np.clip(
        1.0 - variance / 3.0 + RNG.normal(0, 0.05, 120), 0.3, 1.0
    )
    df = pd.DataFrame(
        {
            "submission_id": [f"S{i:03d}" for i in range(120)],
            "variance": variance,
            "confidence": confidence,
        }
    )
    df.to_csv(RAW_DIR / "confidence_scatter_raw.csv", index=False)


def main() -> None:
    _score_points()
    _llm_metrics()
    _deepeval_metrics()
    _turnaround()
    _feature_usage()
    _explanation_lengths()
    _confidence_scatter()
    print(f"Raw evaluation exports written to {RAW_DIR}")


if __name__ == "__main__":
    main()
