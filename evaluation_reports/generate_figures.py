from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
OUTPUT = BASE
DATA = BASE / "data"


def _finalize(fig: plt.Figure, name: str) -> None:
    """Tighten spacing, write to disk, and close the figure."""
    fig.tight_layout()
    path = OUTPUT / name
    fig.savefig(path, dpi=300)
    plt.close(fig)


def figure_accuracy() -> None:
    df = pd.read_csv(DATA / "score_points.csv")
    true_scores = df["lecturer_score"].to_numpy()
    baseline = df["single_agent_score"].to_numpy()
    multi_agent = df["multi_agent_score"].to_numpy()

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(true_scores, baseline, alpha=0.45, label="Single-agent", color="#d95f02")
    ax.scatter(true_scores, multi_agent, alpha=0.55, label="Multi-agent", color="#1b9e77")

    lims = [50, 100]
    ax.plot(lims, lims, "k--", linewidth=1, label="Perfect agreement")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("Lecturer score")
    ax.set_ylabel("AI score")
    ax.set_title("AI vs. lecturer score agreement")
    ax.legend()
    _finalize(fig, "figure_accuracy.png")


def figure_llm_accuracy() -> None:
    df = pd.read_csv(DATA / "llm_metrics.csv")
    models = df["model"].to_list()
    text_acc = df["text_agreement"].to_numpy()
    code_acc = df["code_agreement"].to_numpy()

    x = np.arange(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.bar(x - width / 2, text_acc, width, label="Text", color="#4daf4a")
    ax.bar(x + width / 2, code_acc, width, label="Code", color="#377eb8")

    ax.set_ylim(0.7, 1.0)
    ax.set_ylabel("Agreement with lecturer")
    ax.set_title("LLM accuracy by modality")
    ax.set_xticks(x, models, rotation=10)
    ax.legend()
    _finalize(fig, "figure_llm_accuracy.png")


def figure_llm_cost_latency() -> None:
    df = pd.read_csv(DATA / "llm_metrics.csv")
    models = df["model"].to_list()
    latency = df["latency_seconds"].to_numpy()
    cost = df["cost_per_1k_tokens"].to_numpy()

    x = np.arange(len(models))
    fig, ax1 = plt.subplots(figsize=(6.2, 4.2))

    ax1.bar(x, latency, color="#984ea3", alpha=0.7, label="Latency (s)")
    ax1.set_ylabel("Latency (seconds)")
    ax1.set_xticks(x, models, rotation=10)

    ax2 = ax1.twinx()
    ax2.plot(x, cost, color="#ff7f00", marker="o", linewidth=2, label="Approx. cost ($/1k tok)")
    ax2.set_ylabel("Approx. cost ($/1k tokens)")

    lines = ax1.containers + [ax2.lines[0]]
    labels = [c.get_label() for c in lines]
    ax1.legend(lines, labels, loc="upper left")
    ax1.set_title("Latency and cost snapshot per model")
    _finalize(fig, "figure_llm_cost_latency.png")


def figure_human_vs_ai_gap() -> None:
    groups = ["Single-agent", "Multi-agent"]
    mae = [4.6, 2.8]
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.bar(groups, mae, color=["#d95f02", "#1b9e77"])
    ax.set_ylabel("MAE against lecturer")
    ax.set_title("Human vs. AI grading gap")
    for idx, value in enumerate(mae):
        ax.text(idx, value + 0.1, f"{value:.1f}", ha="center", va="bottom")
    _finalize(fig, "figure_human_vs_ai_gap.png")


def figure_deepeval_metrics() -> None:
    df = pd.read_csv(DATA / "deepeval_metrics.csv")
    metrics = df["metric"].to_list()
    baseline = df["single_agent_score"].to_numpy()
    multi = df["multi_agent_score"].to_numpy()

    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar(x - width / 2, baseline, width, label="Single-agent", color="#fc8d62")
    ax.bar(x + width / 2, multi, width, label="Multi-agent", color="#66c2a5")
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("DeepEval score")
    ax.set_xticks(x, metrics)
    ax.set_title("DeepEval rubric alignment")
    ax.legend()
    _finalize(fig, "figure_deepeval_metrics.png")


def figure_explanation_lengths() -> None:
    lengths = pd.read_csv(DATA / "explanation_lengths.csv")["length"].to_numpy()
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.hist(lengths, bins=16, color="#80b1d3", edgecolor="#03396c")
    ax.set_xlabel("Length (words)")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of explanation lengths")
    _finalize(fig, "figure_explanation_lengths.png")


def figure_confidence_scatter() -> None:
    df = pd.read_csv(DATA / "confidence_scatter.csv")
    variance = df["variance"].to_numpy()
    confidence = df["confidence"].to_numpy()
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    ax.scatter(variance, confidence, alpha=0.6, color="#a6cee3")
    ax.set_xlabel("Agent variance (rubric points)")
    ax.set_ylabel("Confidence score")
    ax.set_title("Confidence vs. agent disagreement")
    _finalize(fig, "figure_confidence_scatter.png")


def figure_turnaround() -> None:
    df = pd.read_csv(DATA / "turnaround.csv")
    cohorts = df["cohort"].to_numpy()
    hours = df["median_hours"].to_numpy()
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.plot(cohorts, hours, marker="o", color="#fb9a99")
    ax.set_ylabel("Median turnaround (hours)")
    ax.set_title("Turnaround time trend")
    _finalize(fig, "figure_turnaround.png")


def figure_usage() -> None:
    df = pd.read_csv(DATA / "feature_usage.csv")
    features = df["feature"].to_list()
    usage = df["share"].to_numpy()
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.barh(features, usage, color="#e78ac3")
    ax.set_xlabel("Share of sessions")
    ax.set_xlim(0, 1)
    ax.set_title("Feature usage during evaluation runs")
    _finalize(fig, "figure_usage.png")


def main() -> None:
    figure_accuracy()
    figure_llm_accuracy()
    figure_llm_cost_latency()
    figure_human_vs_ai_gap()
    figure_deepeval_metrics()
    figure_explanation_lengths()
    figure_confidence_scatter()
    figure_turnaround()
    figure_usage()


if __name__ == "__main__":
    main()
