from pathlib import Path

from cchard_eval.client import EndpointConfig, SyntheticClient
from cchard_eval.data import load_items, load_jsonl
from cchard_eval.inference import run_inference


ROOT = Path(__file__).resolve().parents[1]


def test_inference_writes_records_and_resumes_without_duplicates(tmp_path):
    items = load_items(ROOT / "sample_items.json")[:2]
    models = [EndpointConfig("demo", "synthetic-model", "synthetic://offline", "")]
    client = SyntheticClient(lambda messages, endpoint: "合成候选答案")
    output = tmp_path / "predictions.jsonl"

    first = run_inference(items, models, client, output)
    second = run_inference(items, models, client, output)

    assert len(first) == 2
    assert len(second) == 2
    records = load_jsonl(output)
    assert len(records) == 2
    assert {(record["item_id"], record["model_label"]) for record in records} == {
        (items[0]["id"], "demo"),
        (items[1]["id"], "demo"),
    }
    assert all(record["prediction_status"] == "ok" for record in records)
    assert all(record["prompt_version"] == "cchard-public-1" for record in records)


def test_failed_inference_is_auditable_and_retryable(tmp_path):
    item = load_items(ROOT / "sample_items.json")[:1]
    models = [EndpointConfig("demo", "synthetic-model", "synthetic://offline", "")]
    output = tmp_path / "predictions.jsonl"

    failed = SyntheticClient(lambda messages, endpoint: (_ for _ in ()).throw(RuntimeError("offline failure")))
    run_inference(item, models, failed, output)
    assert load_jsonl(output)[0]["prediction_status"] == "error"
    assert "offline failure" not in load_jsonl(output)[0].get("response", "")

    successful = SyntheticClient(lambda messages, endpoint: "恢复后的答案")
    run_inference(item, models, successful, output)
    records = load_jsonl(output)
    assert len(records) == 2
    assert records[-1]["prediction_status"] == "ok"
