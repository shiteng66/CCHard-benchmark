from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import ChatClient, EndpointConfig
from .data import append_jsonl, load_jsonl
from .prompts import PROMPT_VERSION, candidate_messages


def run_inference(
    items: list[dict[str, Any]],
    models: list[EndpointConfig],
    client: ChatClient,
    output_path: Path | str,
) -> list[dict[str, Any]]:
    target = Path(output_path)
    existing = load_jsonl(target)
    completed = {
        (record.get("item_id"), record.get("model_label"))
        for record in existing
        if record.get("prediction_status") == "ok"
    }
    for model in models:
        for item in items:
            key = (item["id"], model.label)
            if key in completed:
                continue
            result = client.complete(candidate_messages(item), model)
            record = {
                "item_id": item["id"],
                "model_label": model.label,
                "model_identifier": model.model,
                "prompt_version": PROMPT_VERSION,
                "prediction_status": result.status,
                "response": result.content if result.status == "ok" else "",
                "latency_ms": result.latency_ms,
                "attempts": result.attempts,
                "error_type": result.error_type,
                "error_message": result.error_message,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "synthetic": model.base_url.startswith("synthetic://"),
            }
            append_jsonl(target, record)
            if result.status == "ok":
                completed.add(key)
    return load_jsonl(target)

