from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
from typing import Any

from . import __version__
from .client import EndpointConfig, OpenAIChatClient, SyntheticClient
from .data import DataValidationError, load_items, load_jsonl
from .inference import run_inference
from .plotting import create_figures
from .prompts import PROMPT_VERSION
from .scoring import run_scoring
from .statistics import write_summaries


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _endpoint(value: Any) -> EndpointConfig:
    if not isinstance(value, dict):
        raise DataValidationError("endpoint configuration must be an object")
    required = {"label", "model", "base_url", "api_key_env"}
    missing = sorted(required - set(value))
    if missing:
        raise DataValidationError(f"endpoint configuration missing: {', '.join(missing)}")
    if not str(value["base_url"]).startswith(("https://", "http://")):
        raise DataValidationError("real endpoint base_url must start with https:// or http://")
    environment_name = str(value["api_key_env"])
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", environment_name):
        raise DataValidationError("api_key_env must be an uppercase environment variable name")
    return EndpointConfig(
        label=str(value["label"]),
        model=str(value["model"]),
        base_url=str(value["base_url"]).rstrip("/"),
        api_key_env=environment_name,
        temperature=float(value.get("temperature", 0.0)),
        top_p=float(value.get("top_p", 1.0)),
        timeout_s=float(value.get("timeout_s", 120.0)),
        max_retries=int(value.get("max_retries", 3)),
    )


def load_config(path: Path | str) -> tuple[list[EndpointConfig], EndpointConfig, str]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"cannot read model configuration: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("models"), list) or not value["models"]:
        raise DataValidationError("configuration requires a non-empty models list")
    models = [_endpoint(entry) for entry in value["models"]]
    labels = [model.label for model in models]
    if len(labels) != len(set(labels)):
        raise DataValidationError("model labels must be unique")
    judge = _endpoint(value.get("judge"))
    judge = EndpointConfig(
        **{
            **judge.public_dict(),
            "temperature": 0.0,
        }
    )
    return models, judge, _sha256(source)


def _synthetic_handler(messages: list[dict[str, str]], endpoint: EndpointConfig) -> str:
    system = messages[0]["content"] if messages else ""
    if "评分裁判" not in system:
        digest = hashlib.sha256(messages[-1]["content"].encode("utf-8")).hexdigest()[:8]
        return (
            "SYNTHETIC DEMO OUTPUT。该文本仅验证模型调用与记录流程，不代表医学回答或基准成绩。"
            f"演示记录标识：{digest}。"
        )
    marker = "请返回以下结构："
    schema_text = ""
    for message in messages:
        if marker in message["content"]:
            schema_text = message["content"].split(marker, 1)[1]
            break
    schema = json.loads(schema_text)
    for criterion in schema["criteria"]:
        token = hashlib.sha256(
            (messages[1]["content"] + criterion["name"]).encode("utf-8")
        ).digest()[0]
        ratio = 0.55 + (token % 31) / 100
        criterion["score"] = round(float(criterion["max_points"]) * ratio, 2)
    schema["critical_error"] = False
    schema["critical_error_types"] = []
    schema["rationale"] = "SYNTHETIC DEMO：仅用于验证评分、统计与出图管线。"
    schema["judge_status"] = "ok"
    return json.dumps(schema, ensure_ascii=False)


def _write_manifest(
    output: Path,
    *,
    items_path: Path,
    item_count: int,
    model_labels: list[str],
    mode: str,
    synthetic: bool,
    config_hash: str,
) -> Path:
    manifest = {
        "package_version": __version__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "synthetic": synthetic,
        "item_count": item_count,
        "model_labels": model_labels,
        "prompt_version": PROMPT_VERSION,
        "items_sha256": _sha256(items_path),
        "configuration_sha256": config_hash,
        "python_version": platform.python_version(),
    }
    path = output / "run_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _pipeline(
    *,
    items_path: Path,
    output: Path,
    models: list[EndpointConfig],
    judge: EndpointConfig,
    client: Any,
    synthetic: bool,
    config_hash: str,
    resamples: int,
    mode: str,
) -> dict[str, Any]:
    items = load_items(items_path)
    output.mkdir(parents=True, exist_ok=True)
    predictions_path = output / "predictions.jsonl"
    scores_path = output / "scores.jsonl"
    predictions = run_inference(items, models, client, predictions_path)
    scores = run_scoring(items, predictions, judge, client, scores_path)
    summaries = write_summaries(items, scores, output / "summaries", resamples=resamples)
    figures = create_figures(output / "summaries", output / "figures", synthetic=synthetic)
    _write_manifest(
        output,
        items_path=items_path,
        item_count=len(items),
        model_labels=[model.label for model in models],
        mode=mode,
        synthetic=synthetic,
        config_hash=config_hash,
    )
    result = {
        "items": len(items),
        "predictions": len([r for r in predictions if r.get("prediction_status") == "ok"]),
        "scores": len([r for r in scores if r.get("judge_status") == "ok"]),
        "summaries": len(summaries),
        "figures": len(figures),
        "output": str(output),
        "synthetic": synthetic,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


def command_demo(args: argparse.Namespace) -> None:
    models = [EndpointConfig("synthetic-demo", "synthetic-candidate-v1", "synthetic://offline", "")]
    judge = EndpointConfig("synthetic-judge", "synthetic-judge-v1", "synthetic://offline", "")
    _pipeline(
        items_path=Path(args.items),
        output=Path(args.output),
        models=models,
        judge=judge,
        client=SyntheticClient(_synthetic_handler),
        synthetic=True,
        config_hash=hashlib.sha256(b"cchard-synthetic-demo-v1").hexdigest(),
        resamples=args.resamples,
        mode="demo",
    )


def command_infer(args: argparse.Namespace) -> None:
    models, _, _ = load_config(args.config)
    items = load_items(args.items)
    output = Path(args.output)
    records = run_inference(items, models, OpenAIChatClient(), output / "predictions.jsonl")
    print(json.dumps({"records": len(records), "output": str(output / 'predictions.jsonl')}))


def command_score(args: argparse.Namespace) -> None:
    _, judge, _ = load_config(args.config)
    items = load_items(args.items)
    predictions = load_jsonl(args.predictions)
    output = Path(args.output)
    records = run_scoring(items, predictions, judge, OpenAIChatClient(), output / "scores.jsonl")
    print(json.dumps({"records": len(records), "output": str(output / 'scores.jsonl')}))


def command_summarize(args: argparse.Namespace) -> None:
    items = load_items(args.items)
    scores = load_jsonl(args.scores)
    paths = write_summaries(items, scores, args.output, resamples=args.resamples)
    print(json.dumps({name: str(path) for name, path in paths.items()}))


def command_plot(args: argparse.Namespace) -> None:
    paths = create_figures(args.summaries, args.output, synthetic=args.synthetic)
    print(json.dumps({"figures": [str(path) for path in paths]}))


def command_run(args: argparse.Namespace) -> None:
    models, judge, config_hash = load_config(args.config)
    _pipeline(
        items_path=Path(args.items),
        output=Path(args.output),
        models=models,
        judge=judge,
        client=OpenAIChatClient(),
        synthetic=False,
        config_hash=config_hash,
        resamples=args.resamples,
        mode="real_api",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cchard-eval", description="CCHard public reproducibility pipeline")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="run the deterministic offline demonstration")
    demo.add_argument("--items", default=str(ROOT / "sample_items.json"))
    demo.add_argument("--output", default=str(ROOT / "examples" / "demo_outputs"))
    demo.add_argument("--resamples", type=int, default=2000)
    demo.set_defaults(func=command_demo)

    infer = subparsers.add_parser("infer", help="run candidate-model inference")
    infer.add_argument("--items", required=True)
    infer.add_argument("--config", required=True)
    infer.add_argument("--output", required=True)
    infer.set_defaults(func=command_infer)

    score = subparsers.add_parser("score", help="score existing prediction JSONL")
    score.add_argument("--items", required=True)
    score.add_argument("--config", required=True)
    score.add_argument("--predictions", required=True)
    score.add_argument("--output", required=True)
    score.set_defaults(func=command_score)

    summarize = subparsers.add_parser("summarize", help="aggregate valid score JSONL")
    summarize.add_argument("--items", required=True)
    summarize.add_argument("--scores", required=True)
    summarize.add_argument("--output", required=True)
    summarize.add_argument("--resamples", type=int, default=2000)
    summarize.set_defaults(func=command_summarize)

    plot = subparsers.add_parser("plot", help="create figures from summary CSV files")
    plot.add_argument("--summaries", required=True)
    plot.add_argument("--output", required=True)
    plot.add_argument("--synthetic", action="store_true")
    plot.set_defaults(func=command_plot)

    run = subparsers.add_parser("run", help="run inference, scoring, summaries and figures")
    run.add_argument("--items", required=True)
    run.add_argument("--config", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--resamples", type=int, default=2000)
    run.set_defaults(func=command_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (DataValidationError, ValueError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0

