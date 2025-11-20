"""Sanitize evaluation run exports into thesis-friendly aggregates.

This script expects raw CSV exports under ``evaluation_reports/raw``. Each raw
file mirrors the direct output of the evaluation notebooks described in
Chapter~\ref{chap:results}. The script removes student identifiers and any
columns that could deanonymise submissions, then writes aggregate-friendly CSVs
into ``evaluation_reports/data``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
SANITIZED = BASE / "data"
SANITIZED.mkdir(parents=True, exist_ok=True)


def score_points() -> None:
    df = pd.read_csv(RAW / "score_points_raw.csv")
    cols = ["lecturer_score", "single_agent_score", "multi_agent_score"]
    df[cols].to_csv(SANITIZED / "score_points.csv", index=False)


def llm_metrics() -> None:
    df = pd.read_csv(RAW / "llm_metrics_raw.csv")
    cols = [
        "model",
        "text_agreement",
        "code_agreement",
        "latency_seconds",
        "cost_per_1k_tokens",
    ]
    df[cols].to_csv(SANITIZED / "llm_metrics.csv", index=False)


def deepeval_metrics() -> None:
    df = pd.read_csv(RAW / "deepeval_metrics_raw.csv")
    cols = ["metric", "single_agent_score", "multi_agent_score"]
    df[cols].to_csv(SANITIZED / "deepeval_metrics.csv", index=False)


def turnaround() -> None:
    df = pd.read_csv(RAW / "turnaround_raw.csv")
    df = df.rename(columns={"week": "cohort"})
    df[["cohort", "median_hours"]].to_csv(SANITIZED / "turnaround.csv", index=False)


def feature_usage() -> None:
    df = pd.read_csv(RAW / "feature_usage_raw.csv")
    df[["feature", "share"]].to_csv(SANITIZED / "feature_usage.csv", index=False)


def explanation_lengths() -> None:
    df = pd.read_csv(RAW / "explanation_lengths_raw.csv")
    df[["length"]].to_csv(SANITIZED / "explanation_lengths.csv", index=False)


def confidence_scatter() -> None:
    df = pd.read_csv(RAW / "confidence_scatter_raw.csv")
    df[["variance", "confidence"]].to_csv(
        SANITIZED / "confidence_scatter.csv", index=False
    )


def main() -> None:
    score_points()
    llm_metrics()
    deepeval_metrics()
    turnaround()
    feature_usage()
    explanation_lengths()
    confidence_scatter()


if __name__ == "__main__":
    main()
