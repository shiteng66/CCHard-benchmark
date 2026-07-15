# CCHard Public Sample Manifest

## Release status

Public-release candidate, version 0.3.0. The package contains exactly 250 de-identified and copyright-cleaned case-derived task items, created from 50 selected clinical scenarios, plus the public inference, scoring, statistics and plotting workflow.

## Three count layers

- `full_constructed_pool`: approximately 130,000 task-formatted items described in manuscript Section 2.2.
- `evaluation_working_subset`: 24,014 records dynamically selected at a fixed evaluation size to control cost and slow benchmark invalidation; this is the locally exported working subset.
- `public_release_sample`: 250 task items sampled from the working subset after item-level provenance, privacy and copyright review; it reproduces the workflow and is not a performance estimate for the full pool.

## Inclusion criteria

1. Only the previously approved case pool with `source_type=team_authored` or `synthetic` was eligible; all selected records are `team_authored`.
2. Only T05, T07, T08, T10 and T12 were eligible.
3. Every public stem uses newly organized clinical-equivalent wording rather than source-case prose.
4. No name, encounter identifier, exact date, institution, clinician, precise location or rare identifying combination remains.
5. Every item has `deid_applied=true` and all five checklist values set to `true`.

## Exclusion decisions

- T01–T04 remain excluded for copyright/source restrictions.
- T06 and T11 remain excluded because row-level team ownership is not sufficiently clear.
- T09 remains excluded because its gold-standard alignment is uncertain.
- Any case candidate with uncertain provenance, direct identifiers, named institutions, precise locations, incomplete gold sections, insufficient safe facts or suspicious source-text similarity was moved to the internal review list.
- The internal review list and internal IDs are not distributed in this package.

## Sampling method

- Deterministic stratified sampling with 10 strata: five subtasks × two difficulty levels.
- Exactly 25 items per stratum, yielding 250 items.
- Fifty unique scenarios were selected: 25 Expert-Hard and 25 Model-Hard. Each selected scenario was task-formatted once for every approved subtask.
- Within each difficulty, greedy round-robin specialty balancing maximized the number of specialties before allowing a second case from the same specialty.
- Eligible but unselected scenarios were retained in the internal pool and were not counted as exclusions.
- Public IDs run sequentially from `CCHARD-PUB-0001` to `CCHARD-PUB-0250` and cannot be reversed to internal IDs.

## Screening and final counts

- Candidate scenarios screened: 800.
- Eligible scenarios after item-level checks: 633.
- Selected scenarios: 50; public task items: 250.
- Internal review scenarios: 167.
- Eligible but not selected: 583.
- Specialty task-item counts: 乳腺科 20, 产科 20, 儿科 20, 内分泌科 15, 口腔科 10, 呼吸内科 15, 外科 10, 妇科与生殖医学科 10, 心血管内科 10, 急诊与重症医学科 10, 感染科 10, 泌尿外科 10, 消化内科 10, 皮肤科 5, 眼科 10, 神经内科 10, 耳鼻咽喉科 10, 肾内科 5, 肿瘤科 10, 血液科 10, 风湿免疫科 10, 骨科 10.

## De-identification and copyright cleaning

- Names and direct identifiers were removed; candidates carrying unresolved direct-identifier markers were held for review.
- Exact ages were converted to 10-year bands; exact calendar dates and collection times were removed.
- Hospitals, institutional departments, clinicians and precise geographic locations were removed or generalized.
- Clinical facts were condensed, reordered and rewritten; a normalized longest-match scan guarded against long source-text carryover.
- Reference answers were restructured by task and limited to information needed for the public prompt.
- Final scans cover phone/identity numbers, encounter numbers, exact dates, institutions, locations, personal names, internal case IDs and prohibited task categories.

## File boundary

The public package includes the dataset, prompt templates, numeric statistics, code, tests, configurations, documentation, metadata, licenses and a 250-item synthetic demo. It excludes source cases, internal IDs, review records, credentials and unpublished model outputs.
