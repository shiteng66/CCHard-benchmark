from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


COLORS = ["#325d88", "#4c956c", "#f4a261", "#9b5de5", "#e76f51", "#457b9d"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _watermark(fig: Any, synthetic: bool) -> None:
    if synthetic:
        fig.text(
            0.5,
            0.5,
            "SYNTHETIC DEMO",
            ha="center",
            va="center",
            fontsize=34,
            color="#b00020",
            alpha=0.12,
            rotation=25,
            weight="bold",
        )


def _save(fig: Any, base: Path) -> list[Path]:
    outputs = []
    for suffix in (".png", ".pdf"):
        target = base.with_suffix(suffix)
        temporary = target.with_name(target.stem + ".tmp" + suffix)
        fig.savefig(temporary, format=suffix[1:], dpi=220, bbox_inches="tight")
        temporary.replace(target)
        outputs.append(target)
    plt.close(fig)
    return outputs


def _grouped_bars(
    rows: list[dict[str, str]],
    category_key: str,
    title: str,
    caption: str,
    output: Path,
    synthetic: bool,
) -> list[Path]:
    categories = sorted({row[category_key] for row in rows})
    models = sorted({row["model_label"] for row in rows})
    lookup = {(row["model_label"], row[category_key]): row for row in rows}
    x = np.arange(len(categories), dtype=float)
    width = 0.8 / max(1, len(models))
    fig, ax = plt.subplots(figsize=(max(7.2, len(categories) * 1.4), 4.8))
    for index, model in enumerate(models):
        means, low, high = [], [], []
        for category in categories:
            row = lookup.get((model, category))
            if row is None:
                means.append(np.nan)
                low.append(0)
                high.append(0)
            else:
                mean = float(row["mean"])
                means.append(mean)
                low.append(max(0, mean - float(row["ci95_low"])))
                high.append(max(0, float(row["ci95_high"]) - mean))
        positions = x - 0.4 + width / 2 + index * width
        ax.bar(
            positions,
            means,
            width,
            label=model,
            color=COLORS[index % len(COLORS)],
            yerr=np.asarray([low, high]),
            capsize=3,
            edgecolor="white",
            linewidth=0.6,
        )
    ax.set_title(title, loc="left", weight="bold")
    ax.set_ylabel("Mean score (0–100)")
    ax.set_ylim(0, 100)
    ax.set_xticks(x, [category.split("_")[0] for category in categories])
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=min(3, max(1, len(models))))
    fig.text(0.01, 0.01, caption, fontsize=8, color="#555555")
    _watermark(fig, synthetic)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, output)


def _heatmap(rows: list[dict[str, str]], output: Path, synthetic: bool) -> list[Path]:
    tasks = sorted({row["subtask"] for row in rows})
    models = sorted({row["model_label"] for row in rows})
    lookup = {(row["model_label"], row["subtask"]): float(row["mean"]) for row in rows}
    matrix = np.full((len(models), len(tasks)), np.nan)
    for i, model in enumerate(models):
        for j, task in enumerate(tasks):
            matrix[i, j] = lookup.get((model, task), np.nan)
    fig, ax = plt.subplots(figsize=(max(7.2, len(tasks) * 1.3), max(3.2, len(models) * 0.7 + 2)))
    image = ax.imshow(matrix, vmin=0, vmax=100, cmap="Blues", aspect="auto")
    for i in range(len(models)):
        for j in range(len(tasks)):
            value = matrix[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", color="white" if value > 58 else "#202020")
    ax.set_xticks(range(len(tasks)), [task.split("_")[0] for task in tasks])
    ax.set_yticks(range(len(models)), models)
    ax.set_title("CCHard public-sample capability profile", loc="left", weight="bold")
    fig.colorbar(image, ax=ax, label="Mean score")
    fig.text(0.01, 0.01, "Input: summary_by_subtask.csv; descriptive public-sample results only.", fontsize=8, color="#555555")
    _watermark(fig, synthetic)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, output)


def create_figures(
    summary_dir: Path | str,
    figure_dir: Path | str,
    *,
    synthetic: bool = False,
) -> list[Path]:
    summaries = Path(summary_dir)
    output = Path(figure_dir)
    output.mkdir(parents=True, exist_ok=True)
    subtask_rows = _read_csv(summaries / "summary_by_subtask.csv")
    difficulty_rows = _read_csv(summaries / "summary_by_difficulty.csv")
    if not subtask_rows or not difficulty_rows:
        raise ValueError("summary CSV files contain no valid score rows")
    files = []
    files.extend(
        _grouped_bars(
            subtask_rows,
            "subtask",
            "Score by public CCHard subtask",
            "Input: summary_by_subtask.csv; bars show mean and percentile 95% bootstrap CI.",
            output / "score_by_subtask",
            synthetic,
        )
    )
    files.extend(
        _grouped_bars(
            difficulty_rows,
            "difficulty",
            "Score by difficulty stratum",
            "Input: summary_by_difficulty.csv; public sample is not representative of the full benchmark.",
            output / "score_by_difficulty",
            synthetic,
        )
    )
    files.extend(_heatmap(subtask_rows, output / "capability_heatmap", synthetic))
    return files

