from __future__ import annotations

import csv
import math
from pathlib import Path
import tempfile
from typing import Any, Iterable

import numpy as np


STAT_FIELDS = ["n", "mean", "std", "median", "ci95_low", "ci95_high"]


def bootstrap_summary(
    values: Iterable[float],
    *,
    seed: int = 20260714,
    resamples: int = 2000,
) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("bootstrap values must be a non-empty finite sequence")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    rng = np.random.default_rng(seed)
    indexes = rng.integers(0, array.size, size=(resamples, array.size))
    means = array[indexes].mean(axis=1)
    return {
        "n": int(array.size),
        "mean": round(float(array.mean()), 6),
        "std": round(float(array.std(ddof=1)) if array.size > 1 else 0.0, 6),
        "median": round(float(np.median(array)), 6),
        "ci95_low": round(float(np.percentile(means, 2.5)), 6),
        "ci95_high": round(float(np.percentile(means, 97.5)), 6),
    }


def _valid_scores(
    items: list[dict[str, Any]], scores: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    item_by_id = {item["id"]: item for item in items}
    valid: list[dict[str, Any]] = []
    for record in scores:
        if record.get("prediction_status") != "ok" or record.get("judge_status") != "ok":
            continue
        score = record.get("final_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            continue
        item = item_by_id.get(str(record.get("item_id", "")))
        if item is None:
            continue
        valid.append(
            {
                **record,
                "dimension": item["dimension"],
                "subtask": item["subtask"],
                "difficulty": item["difficulty"],
                "specialty": item["specialty"],
                "final_score": float(score),
            }
        )
    return valid


def _group_rows(
    records: list[dict[str, Any]],
    keys: list[str],
    *,
    seed: int,
    resamples: int,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[float]] = {}
    for record in records:
        key = tuple(str(record.get(name, "")) for name in keys)
        groups.setdefault(key, []).append(float(record["final_score"]))
    rows = []
    for index, (group, values) in enumerate(sorted(groups.items())):
        row = {name: value for name, value in zip(keys, group)}
        row.update(bootstrap_summary(values, seed=seed + index, resamples=resamples))
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
        temporary = Path(handle.name)
    temporary.replace(path)


def write_summaries(
    items: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    output_dir: Path | str,
    *,
    seed: int = 20260714,
    resamples: int = 2000,
) -> dict[str, Path]:
    output = Path(output_dir)
    records = _valid_scores(items, scores)
    definitions = {
        "overall": (["model_label"], "summary_overall.csv"),
        "subtask": (["model_label", "subtask"], "summary_by_subtask.csv"),
        "difficulty": (["model_label", "difficulty"], "summary_by_difficulty.csv"),
        "dimension": (["model_label", "dimension"], "summary_by_dimension.csv"),
    }
    paths: dict[str, Path] = {}
    for offset, (name, (keys, filename)) in enumerate(definitions.items()):
        rows = _group_rows(records, keys, seed=seed + offset * 1000, resamples=resamples)
        path = output / filename
        _write_csv(path, rows, keys + STAT_FIELDS)
        paths[name] = path

    difficulty_groups: dict[tuple[str, str, str], list[float]] = {}
    for record in records:
        key = (record["model_label"], record["subtask"], record["difficulty"])
        difficulty_groups.setdefault(key, []).append(record["final_score"])
    gap_rows = []
    pairs = sorted({(model, subtask) for model, subtask, _ in difficulty_groups})
    for model, subtask in pairs:
        expert = difficulty_groups.get((model, subtask, "Expert-Hard"), [])
        model_hard = difficulty_groups.get((model, subtask, "Model-Hard"), [])
        if not expert or not model_hard:
            continue
        expert_mean = float(np.mean(expert))
        model_mean = float(np.mean(model_hard))
        gap_rows.append(
            {
                "model_label": model,
                "subtask": subtask,
                "expert_hard_n": len(expert),
                "expert_hard_mean": round(expert_mean, 6),
                "model_hard_n": len(model_hard),
                "model_hard_mean": round(model_mean, 6),
                "model_hard_minus_expert_hard": round(model_mean - expert_mean, 6),
            }
        )
    gap_path = output / "difficulty_gaps.csv"
    _write_csv(
        gap_path,
        gap_rows,
        [
            "model_label",
            "subtask",
            "expert_hard_n",
            "expert_hard_mean",
            "model_hard_n",
            "model_hard_mean",
            "model_hard_minus_expert_hard",
        ],
    )
    paths["difficulty_gaps"] = gap_path
    return paths

