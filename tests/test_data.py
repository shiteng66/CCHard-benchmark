import json
from pathlib import Path

import pytest

from cchard_eval.data import DataValidationError, append_jsonl, load_items, load_jsonl


ROOT = Path(__file__).resolve().parents[1]


def test_loads_all_public_items():
    items = load_items(ROOT / "sample_items.json")
    assert len(items) == 250
    assert {item["subtask"] for item in items} == {
        "T05_diagnosis",
        "T07_evidence",
        "T08_differential",
        "T10_examination",
        "T12_treatment",
    }


def test_rejects_duplicate_public_ids(tmp_path):
    items = json.loads((ROOT / "sample_items.json").read_text(encoding="utf-8"))
    items[1]["id"] = items[0]["id"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(DataValidationError, match="duplicate id"):
        load_items(path)


def test_rejects_missing_rubric(tmp_path):
    items = json.loads((ROOT / "sample_items.json").read_text(encoding="utf-8"))
    del items[0]["rubric"]
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(DataValidationError, match="rubric"):
        load_items(path)


def test_jsonl_round_trip(tmp_path):
    path = tmp_path / "records.jsonl"
    append_jsonl(path, {"id": "a", "text": "中文"})
    append_jsonl(path, {"id": "b", "value": 2})
    assert load_jsonl(path) == [
        {"id": "a", "text": "中文"},
        {"id": "b", "value": 2},
    ]

