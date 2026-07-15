import csv
from pathlib import Path

from cchard_eval.data import load_items
from cchard_eval.statistics import bootstrap_summary, write_summaries


ROOT = Path(__file__).resolve().parents[1]


def score_record(item, score, model="demo", status="ok"):
    return {
        "item_id": item["id"],
        "model_label": model,
        "prediction_status": "ok",
        "judge_status": status,
        "final_score": score if status == "ok" else None,
        "synthetic": True,
    }


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_bootstrap_summary_is_deterministic():
    first = bootstrap_summary([10, 20, 30, 40], seed=7, resamples=500)
    second = bootstrap_summary([10, 20, 30, 40], seed=7, resamples=500)
    assert first == second
    assert first["n"] == 4
    assert first["mean"] == 25
    assert first["ci95_low"] <= first["mean"] <= first["ci95_high"]


def test_writes_grouped_summaries_and_excludes_errors(tmp_path):
    items = load_items(ROOT / "sample_items.json")
    scores = [score_record(item, 80 if item["difficulty"] == "Expert-Hard" else 60) for item in items]
    scores.append(score_record(items[0], None, model="broken", status="error"))
    paths = write_summaries(items, scores, tmp_path)

    assert set(paths) == {"overall", "subtask", "difficulty", "dimension", "difficulty_gaps"}
    overall = read_csv(paths["overall"])
    assert [row["model_label"] for row in overall] == ["demo"]
    assert int(overall[0]["n"]) == 250

    by_subtask = read_csv(paths["subtask"])
    assert len(by_subtask) == 5
    assert {row["subtask"] for row in by_subtask} == {
        "T05_diagnosis",
        "T07_evidence",
        "T08_differential",
        "T10_examination",
        "T12_treatment",
    }

    gaps = read_csv(paths["difficulty_gaps"])
    assert len(gaps) == 5
    assert all(float(row["model_hard_minus_expert_hard"]) == -20 for row in gaps)

