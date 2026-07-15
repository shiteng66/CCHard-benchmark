from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any

from .client import ChatClient, EndpointConfig
from .data import append_jsonl, load_jsonl
from .prompts import PROMPT_VERSION, judge_messages


class JudgementValidationError(ValueError):
    """Raised when an LLM judgement cannot satisfy the released rubric."""


def parse_judge_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise JudgementValidationError("judge response is not valid JSON")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise JudgementValidationError("judge response is not valid JSON") from exc
    if not isinstance(value, dict):
        raise JudgementValidationError("judge JSON must be an object")
    return value


def validate_judgement(item: dict[str, Any], judgement: dict[str, Any]) -> dict[str, Any]:
    rubric = item["rubric"]
    expected = {criterion["name"]: float(criterion["points"]) for criterion in rubric["criteria"]}
    supplied = judgement.get("criteria")
    if not isinstance(supplied, list):
        raise JudgementValidationError("criteria must be a list")
    by_name: dict[str, dict[str, Any]] = {}
    for criterion in supplied:
        if not isinstance(criterion, dict) or not isinstance(criterion.get("name"), str):
            raise JudgementValidationError("each criterion requires a name")
        name = criterion["name"]
        if name in by_name:
            raise JudgementValidationError(f"duplicate criterion: {name}")
        by_name[name] = criterion
    if set(by_name) != set(expected):
        raise JudgementValidationError("criterion names must exactly match the rubric")

    normalized_criteria = []
    raw_score = 0.0
    for rubric_criterion in rubric["criteria"]:
        name = rubric_criterion["name"]
        maximum = float(rubric_criterion["points"])
        value = by_name[name].get("score")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise JudgementValidationError(f"criterion score is not finite: {name}")
        score = float(value)
        if score < 0 or score > maximum:
            raise JudgementValidationError(f"criterion score outside 0-{maximum:g}: {name}")
        raw_score += score
        normalized_criteria.append(
            {
                "name": name,
                "score": round(score, 6),
                "max_points": rubric_criterion["points"],
            }
        )

    critical_error = judgement.get("critical_error")
    if not isinstance(critical_error, bool):
        raise JudgementValidationError("critical_error must be boolean")
    error_types = judgement.get("critical_error_types", [])
    if not isinstance(error_types, list) or not all(isinstance(value, str) for value in error_types):
        raise JudgementValidationError("critical_error_types must be a string list")
    allowed_errors = set(rubric["critical_errors"])
    if not set(error_types).issubset(allowed_errors):
        raise JudgementValidationError("critical_error_types contains a value outside the rubric")
    if critical_error and not error_types:
        raise JudgementValidationError("critical_error requires at least one critical_error_type")
    if not critical_error and error_types:
        raise JudgementValidationError("critical_error_types must be empty when critical_error is false")
    rationale = judgement.get("rationale", "")
    if not isinstance(rationale, str):
        raise JudgementValidationError("rationale must be a string")

    raw_score = round(raw_score, 6)
    final_score = round(min(raw_score, 20.0) if critical_error else raw_score, 6)
    return {
        "criteria": normalized_criteria,
        "raw_score": raw_score,
        "final_score": final_score,
        "critical_error": critical_error,
        "critical_error_types": error_types,
        "rationale": rationale[:1000],
    }


def _error_record(
    item: dict[str, Any],
    prediction: dict[str, Any],
    judge: EndpointConfig,
    *,
    error_type: str,
    error_message: str,
    repair_attempted: bool,
) -> dict[str, Any]:
    return {
        "item_id": item["id"],
        "model_label": prediction.get("model_label", ""),
        "model_identifier": prediction.get("model_identifier", ""),
        "dimension": item["dimension"],
        "subtask": item["subtask"],
        "specialty": item["specialty"],
        "difficulty": item["difficulty"],
        "prediction_status": prediction.get("prediction_status", "error"),
        "judge_status": "error",
        "judge_identifier": judge.model,
        "prompt_version": PROMPT_VERSION,
        "criteria": [],
        "raw_score": None,
        "final_score": None,
        "critical_error": None,
        "critical_error_types": [],
        "rationale": "",
        "repair_attempted": repair_attempted,
        "error_type": error_type,
        "error_message": error_message[:500],
        "synthetic": bool(prediction.get("synthetic")) or judge.base_url.startswith("synthetic://"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_scoring(
    items: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    judge_config: EndpointConfig,
    client: ChatClient,
    output_path: Path | str,
) -> list[dict[str, Any]]:
    target = Path(output_path)
    item_by_id = {item["id"]: item for item in items}
    latest_predictions: dict[tuple[str, str], dict[str, Any]] = {}
    for prediction in predictions:
        key = (str(prediction.get("item_id", "")), str(prediction.get("model_label", "")))
        latest_predictions[key] = prediction

    existing = load_jsonl(target)
    completed = {
        (record.get("item_id"), record.get("model_label"))
        for record in existing
        if record.get("judge_status") == "ok"
    }
    for key, prediction in latest_predictions.items():
        if key in completed:
            continue
        item = item_by_id.get(key[0])
        if item is None:
            continue
        if prediction.get("prediction_status") != "ok":
            append_jsonl(
                target,
                _error_record(
                    item,
                    prediction,
                    judge_config,
                    error_type="prediction_error",
                    error_message=str(prediction.get("error_type", "candidate inference failed")),
                    repair_attempted=False,
                ),
            )
            continue

        first = client.complete(judge_messages(item, str(prediction.get("response", ""))), judge_config)
        if first.status != "ok":
            append_jsonl(
                target,
                _error_record(
                    item,
                    prediction,
                    judge_config,
                    error_type=first.error_type or "judge_api_error",
                    error_message=first.error_message,
                    repair_attempted=False,
                ),
            )
            continue

        repair_attempted = False
        response_text = first.content
        try:
            normalized = validate_judgement(item, parse_judge_json(response_text))
        except JudgementValidationError as first_error:
            repair_attempted = True
            repair = client.complete(
                judge_messages(
                    item,
                    str(prediction.get("response", "")),
                    repair=True,
                    previous_response=response_text,
                ),
                judge_config,
            )
            if repair.status != "ok":
                append_jsonl(
                    target,
                    _error_record(
                        item,
                        prediction,
                        judge_config,
                        error_type=repair.error_type or "judge_repair_api_error",
                        error_message=repair.error_message,
                        repair_attempted=True,
                    ),
                )
                continue
            try:
                normalized = validate_judgement(item, parse_judge_json(repair.content))
            except JudgementValidationError as repair_error:
                append_jsonl(
                    target,
                    _error_record(
                        item,
                        prediction,
                        judge_config,
                        error_type="judge_validation_error",
                        error_message=f"{first_error}; repair: {repair_error}",
                        repair_attempted=True,
                    ),
                )
                continue

        record = {
            "item_id": item["id"],
            "model_label": prediction["model_label"],
            "model_identifier": prediction.get("model_identifier", ""),
            "dimension": item["dimension"],
            "subtask": item["subtask"],
            "specialty": item["specialty"],
            "difficulty": item["difficulty"],
            "prediction_status": "ok",
            "judge_status": "ok",
            "judge_identifier": judge_config.model,
            "prompt_version": PROMPT_VERSION,
            **normalized,
            "repair_attempted": repair_attempted,
            "error_type": "",
            "error_message": "",
            "synthetic": bool(prediction.get("synthetic")) or judge_config.base_url.startswith("synthetic://"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        append_jsonl(target, record)
        completed.add(key)
    return load_jsonl(target)

