import json
from pathlib import Path

from cchard_eval.data import load_items
from cchard_eval.prompts import PROMPT_VERSION, candidate_messages, judge_messages


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_prompt_contains_only_public_task_material():
    item = load_items(ROOT / "sample_items.json")[0]
    messages = candidate_messages(item)
    text = "\n".join(message["content"] for message in messages)
    assert item["stem"] in text
    assert item["question"] in text
    assert item["id"] not in text
    assert "reference_answer" not in text
    assert PROMPT_VERSION == "cchard-public-1"


def test_judge_prompt_contains_released_answer_and_exact_rubric():
    item = load_items(ROOT / "sample_items.json")[0]
    messages = judge_messages(item, "候选模型答案")
    text = "\n".join(message["content"] for message in messages)
    assert "候选模型答案" in text
    assert json.dumps(item["reference_answer"], ensure_ascii=False) in text
    for criterion in item["rubric"]["criteria"]:
        assert criterion["name"] in text
        assert str(criterion["points"]) in text


def test_repair_prompt_requests_json_only():
    item = load_items(ROOT / "sample_items.json")[0]
    messages = judge_messages(item, "候选模型答案", repair=True, previous_response="not json")
    assert messages[-1]["role"] == "user"
    assert "not json" in messages[-1]["content"]
    assert "仅输出修复后的JSON" in messages[-1]["content"]
