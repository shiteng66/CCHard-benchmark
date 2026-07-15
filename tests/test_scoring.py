import json
from pathlib import Path

import pytest

from cchard_eval.client import EndpointConfig, SyntheticClient
from cchard_eval.data import load_items, load_jsonl
from cchard_eval.scoring import JudgementValidationError, run_scoring, validate_judgement


ROOT = Path(__file__).resolve().parents[1]


def judgement_for(item, score=10, critical=False):
    criteria = []
    for criterion in item["rubric"]["criteria"]:
        criteria.append(
            {
                "name": criterion["name"],
                "score": min(score, criterion["points"]),
                "max_points": criterion["points"],
            }
        )
    return {
        "criteria": criteria,
        "critical_error": critical,
        "critical_error_types": [item["rubric"]["critical_errors"][0]] if critical else [],
        "rationale": "合成评分",
        "judge_status": "ok",
        "final_score": 999,
    }


def test_total_is_recalculated_and_ignores_model_total():
    item = load_items(ROOT / "sample_items.json")[0]
    judgement = judgement_for(item, score=10)
    result = validate_judgement(item, judgement)
    assert result["raw_score"] == 50
    assert result["final_score"] == 50
    assert result["final_score"] != judgement["final_score"]


def test_rejects_criterion_score_above_maximum():
    item = load_items(ROOT / "sample_items.json")[0]
    judgement = judgement_for(item)
    judgement["criteria"][0]["score"] = item["rubric"]["criteria"][0]["points"] + 1
    with pytest.raises(JudgementValidationError, match="outside"):
        validate_judgement(item, judgement)


def test_critical_error_caps_final_score_at_twenty():
    item = load_items(ROOT / "sample_items.json")[0]
    judgement = judgement_for(item, score=100, critical=True)
    result = validate_judgement(item, judgement)
    assert result["raw_score"] == 100
    assert result["final_score"] == 20


def test_invalid_json_gets_one_repair_and_then_scores(tmp_path):
    item = load_items(ROOT / "sample_items.json")[0]
    prediction = {
        "item_id": item["id"],
        "model_label": "demo",
        "model_identifier": "synthetic-model",
        "prediction_status": "ok",
        "response": "候选答案",
        "synthetic": True,
    }
    calls = {"count": 0}

    def handler(messages, config):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not json"
        return json.dumps(judgement_for(item), ensure_ascii=False)

    output = tmp_path / "scores.jsonl"
    client = SyntheticClient(handler)
    config = EndpointConfig("judge", "synthetic-judge", "synthetic://offline", "")
    records = run_scoring([item], [prediction], config, client, output)
    assert calls["count"] == 2
    assert records[0]["judge_status"] == "ok"
    assert records[0]["repair_attempted"] is True


def test_persistent_invalid_judge_response_is_not_numeric_and_can_retry(tmp_path):
    item = load_items(ROOT / "sample_items.json")[0]
    prediction = {
        "item_id": item["id"],
        "model_label": "demo",
        "model_identifier": "synthetic-model",
        "prediction_status": "ok",
        "response": "候选答案",
        "synthetic": True,
    }
    output = tmp_path / "scores.jsonl"
    config = EndpointConfig("judge", "synthetic-judge", "synthetic://offline", "")
    bad = SyntheticClient(lambda messages, endpoint: "still not json")
    run_scoring([item], [prediction], config, bad, output)
    failed = load_jsonl(output)[0]
    assert failed["judge_status"] == "error"
    assert failed["final_score"] is None

    good = SyntheticClient(lambda messages, endpoint: json.dumps(judgement_for(item), ensure_ascii=False))
    run_scoring([item], [prediction], config, good, output)
    records = load_jsonl(output)
    assert len(records) == 2
    assert records[-1]["judge_status"] == "ok"


def test_successful_score_resume_does_not_duplicate(tmp_path):
    item = load_items(ROOT / "sample_items.json")[0]
    prediction = {
        "item_id": item["id"],
        "model_label": "demo",
        "model_identifier": "synthetic-model",
        "prediction_status": "ok",
        "response": "候选答案",
        "synthetic": True,
    }
    output = tmp_path / "scores.jsonl"
    config = EndpointConfig("judge", "synthetic-judge", "synthetic://offline", "")
    client = SyntheticClient(lambda messages, endpoint: json.dumps(judgement_for(item), ensure_ascii=False))
    run_scoring([item], [prediction], config, client, output)
    run_scoring([item], [prediction], config, client, output)
    assert len(load_jsonl(output)) == 1
