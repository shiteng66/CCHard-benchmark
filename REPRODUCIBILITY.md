# CCHard Public Reproducibility Workflow

This release contains a clean-room reference implementation of the public CCHard evaluation workflow: model inference, rubric-based automatic scoring, statistical aggregation and figure generation.

本版本提供公开样例的最小可复现代码，包括模型调用、自动评分、统计汇总和出图。它不包含内部题库、历史脚本、私有接口或任何真实 API Key。

## Scope

The code supports the 250 released items from T05, T07, T08, T10 and T12. It demonstrates the published evaluation mechanics but cannot reproduce the manuscript's full-benchmark numerical results because the full 12-task item bank and original model outputs are not public.

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[test]"
```

Python 3.10 or newer is required.

## Offline reproducibility check

No key or network access is needed:

```bash
cchard-eval demo --output outputs/demo
pytest -q
```

The demo uses explicitly synthetic candidate and judge outputs. Its figures carry a `SYNTHETIC DEMO` watermark and must not be reported as benchmark performance.

## Real model evaluation

1. Copy `configs/models.example.json` and replace only model identifiers and endpoint URLs.
2. Export credentials using the environment-variable names referenced by the configuration.
3. Run the pipeline:

```bash
export CCHARD_CANDIDATE_API_KEY="your-secret-in-the-shell-only"
export CCHARD_JUDGE_API_KEY="your-secret-in-the-shell-only"

cchard-eval run \
  --items sample_items.json \
  --config configs/models.example.json \
  --output outputs/real_run
```

The CLI intentionally has no command-line API-key option. Secrets are never written to output records or the run manifest.

## Staged commands

```bash
cchard-eval infer --items sample_items.json --config configs/models.example.json --output outputs/run
cchard-eval score --items sample_items.json --config configs/models.example.json --predictions outputs/run/predictions.jsonl --output outputs/run
cchard-eval summarize --items sample_items.json --scores outputs/run/scores.jsonl --output outputs/run/summaries
cchard-eval plot --summaries outputs/run/summaries --output outputs/run/figures
```

Successful `(item_id, model_label)` records are resumable. Failed requests remain explicit error records and can be retried; they are excluded from numeric summaries rather than assigned zero.

## Outputs

- `predictions.jsonl`: one auditable candidate-call record per item/model attempt.
- `scores.jsonl`: criterion-level rubric scores, safety flags and judge status.
- `summaries/*.csv`: mean, standard deviation, median and percentile 95% bootstrap interval.
- `figures/*.png` and `figures/*.pdf`: subtask, difficulty and capability-profile figures.
- `run_manifest.json`: package/prompt versions and input/configuration hashes without secrets.

The public scorer recalculates totals locally. Criterion scores must match every released rubric item and stay within its maximum. A released critical-error finding caps the public reference score at 20. Persistent invalid judge responses remain non-numeric errors.

## Statistical interpretation

Bootstrap uses 2,000 resamples and seed `20260714` by default. The 250-item sample is for workflow verification and is not statistically representative of the full CCHard benchmark. The code therefore produces descriptive summaries and does not automatically claim statistical significance.

## Licensing

Code under `src/` and `tests/` is licensed under the MIT License (`LICENSE_CODE`). Dataset items and dataset documentation remain under CC BY-NC 4.0 (`LICENSE`).

