# CCHard Public Reproducibility Sample

Version 0.3.0 · Released 2026-07-14

This package contains 250 copyright-cleared, fully de-identified case–task items — derived from **50 unique de-identified clinical cases, each posed under the five case-based subtasks** (50 cases × 5 subtasks = 250 case–task items) — together with a runnable public evaluation pipeline accompanying the manuscript **CCHard: A Multidimensional Medical LLM Benchmark for Complex Clinical Tasks**.

本包包含 250 条病例–任务条目（来自 50 个唯一脱敏病例，每个病例在 5 个病例型子任务下各出一题：50 病例 × 5 子任务 = 250 条），均经版权筛选与去标识化；附可运行的模型调用、自动评分、统计和出图代码。

## What is included

- 250 open-ended items from five approved case-based subtasks: T05 diagnosis, T07 diagnostic evidence, T08 differential diagnosis, T10 examination recommendation and T12 treatment planning.
- Exactly 25 items in every subtask × difficulty stratum: 125 Expert-Hard and 125 Model-Hard items.
- The 250 items come from **50 unique de-identified cases**, each appearing once per subtask with a task-specific question and reference answer (50 cases × 5 subtasks = 250 case–task items; see `statistics.json` → `public_release_sample.unique_case_scenarios`).
- Structured reference answers, explicit 0–100 rubrics, task prompt templates, JSON/CSV data, numeric statistics and release metadata.
- Clean-room Python code for OpenAI-compatible model calls, resumable JSONL output, rubric-based LLM-assisted scoring, deterministic bootstrap summaries and PNG/PDF figures.
- A credential-free synthetic demo and offline tests. All demo results are visibly labelled `SYNTHETIC DEMO` and are not benchmark results.

## Three count layers

The full constructed pool contains approximately **130,000** task-formatted items; evaluation uses a dynamically selected fixed-size working subset of **24,014** items to control evaluation cost and reduce benchmark invalidation; this public release contains **250** items sampled from that working subset solely to reproduce the workflow and does not represent full-benchmark performance.

全库约 13 万条为构建总量；评测采用动态筛选的固定题量工作子集（24,014 条），以控制评测成本并减缓基准失效；公开样例 250 条抽自该工作子集，仅用于复现流程，不代表全库成绩。

The scopes are nested, not competing totals: `full_constructed_pool` → `evaluation_working_subset` → `public_release_sample`. See `statistics.json`.

## What is deliberately excluded

- T01–T04 textbook, guideline, terminology-source and professional-examination records because they cannot be redistributed safely.
- T06 and T11 because row-level team ownership remains unclear.
- T09 because the reliability of its gold alignment remains uncertain.
- Names, encounter identifiers, exact dates, institutions, physicians, precise locations and rare identifying combinations.
- Internal IDs, source cases, `review_needed.json`, private configuration, credentials and internal scripts.

## Quick reproducibility check

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
cchard-eval demo --output outputs/demo
pytest -q
```

The demo requires no network access or API key. See `REPRODUCIBILITY.md` for real-model configuration and staged commands. The package is not a clinical decision-support system and must not be used for diagnosis, treatment or patient care.

## Code and data availability

The released code implements inference, automatic rubric scoring, summaries and figures for the public sample. It verifies the published mechanics but cannot independently reproduce the manuscript's full-benchmark numerical results because the unpublished item bank and original model outputs are not included. See `CODE_AVAILABILITY_STATEMENT.md` and `DATA_AVAILABILITY_STATEMENT.md`.

## Provenance, privacy and copyright

All 250 records were drawn only from the previously approved team-authored case pool. Each public stem was reconstructed as a clinical equivalent, exact ages were converted to 10-year bands, and direct or indirect identifiers were removed or generalized. Items with uncertain ownership, privacy status, or text safety were conservatively held for internal review.

## Licenses

- Dataset items and dataset documentation: CC BY-NC 4.0 (`LICENSE`).
- Original software under `src/` and `tests/`: MIT License (`LICENSE_CODE`).

Third-party source materials are not included and are not relicensed. Use `CITATION.cff`; add final article and Zenodo DOIs after assignment.
