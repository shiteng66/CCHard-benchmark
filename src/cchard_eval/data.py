from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PUBLIC_SUBTASKS = {
    "T05_diagnosis",
    "T07_evidence",
    "T08_differential",
    "T10_examination",
    "T12_treatment",
}

REQUIRED_FIELDS = {
    "id",
    "dimension",
    "subtask",
    "specialty",
    "difficulty",
    "stem",
    "question",
    "options",
    "reference_answer",
    "rubric",
    "source_type",
    "deid_applied",
    "deid_checklist",
    "notes",
}


class DataValidationError(ValueError):
    """Raised when a public release record violates the published schema."""


def _validate_rubric(item_id: str, rubric: Any) -> None:
    if not isinstance(rubric, dict):
        raise DataValidationError(f"{item_id}: rubric must be an object")
    if rubric.get("scale") != [0, 100]:
        raise DataValidationError(f"{item_id}: rubric scale must be [0, 100]")
    criteria = rubric.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise DataValidationError(f"{item_id}: rubric criteria must be non-empty")
    names: list[str] = []
    total = 0.0
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise DataValidationError(f"{item_id}: rubric criterion must be an object")
        name = criterion.get("name")
        points = criterion.get("points")
        if not isinstance(name, str) or not name.strip():
            raise DataValidationError(f"{item_id}: rubric criterion name is required")
        if isinstance(points, bool) or not isinstance(points, (int, float)) or points <= 0:
            raise DataValidationError(f"{item_id}: rubric criterion points must be positive")
        names.append(name)
        total += float(points)
    if len(names) != len(set(names)):
        raise DataValidationError(f"{item_id}: duplicate rubric criterion name")
    if abs(total - 100.0) > 1e-9:
        raise DataValidationError(f"{item_id}: rubric criterion points must sum to 100")
    critical = rubric.get("critical_errors")
    if not isinstance(critical, list) or not all(isinstance(value, str) and value for value in critical):
        raise DataValidationError(f"{item_id}: rubric critical_errors must be a string list")


def validate_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise DataValidationError("each item must be an object")
    missing = sorted(REQUIRED_FIELDS - set(item))
    if missing:
        raise DataValidationError(f"item missing required fields: {', '.join(missing)}")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.startswith("CCHARD-PUB-"):
        raise DataValidationError("item id must use CCHARD-PUB- prefix")
    if item.get("subtask") not in PUBLIC_SUBTASKS:
        raise DataValidationError(f"{item_id}: unsupported public subtask")
    if item.get("difficulty") not in {"Expert-Hard", "Model-Hard"}:
        raise DataValidationError(f"{item_id}: invalid difficulty")
    if item.get("source_type") not in {"team_authored", "synthetic"}:
        raise DataValidationError(f"{item_id}: invalid source_type")
    if item.get("deid_applied") is not True:
        raise DataValidationError(f"{item_id}: deid_applied must be true")
    checklist = item.get("deid_checklist")
    if not isinstance(checklist, dict) or not checklist or not all(value is True for value in checklist.values()):
        raise DataValidationError(f"{item_id}: all deid_checklist values must be true")
    if not isinstance(item.get("stem"), str) or not item["stem"].strip():
        raise DataValidationError(f"{item_id}: stem is required")
    if not isinstance(item.get("question"), str) or not item["question"].strip():
        raise DataValidationError(f"{item_id}: question is required")
    if not isinstance(item.get("reference_answer"), dict):
        raise DataValidationError(f"{item_id}: reference_answer must be an object")
    _validate_rubric(item_id, item.get("rubric"))
    return item


def load_items(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"cannot read items from {source}: {exc}") from exc
    if not isinstance(data, list):
        raise DataValidationError("sample_items.json must contain a JSON array")
    items = [validate_item(item) for item in data]
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise DataValidationError("duplicate id in sample_items.json")
    return items


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DataValidationError(f"{source}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise DataValidationError(f"{source}:{line_number}: JSONL record must be an object")
        records.append(record)
    return records


def append_jsonl(path: Path | str, record: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")

