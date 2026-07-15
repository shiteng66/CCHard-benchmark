# CCHard Public Sample Data Dictionary / CCHard 公开样例数据字典

## File conventions / 文件约定

- Encoding / 编码：UTF-8。
- `sample_items.json` is a JSON array; one object is one task item. / `sample_items.json` 为 JSON 数组，每个对象为一个任务条目。
- `sample_items.csv` uses one row per task item. Nested fields are compact JSON strings. / `sample_items.csv` 每行一个任务条目，嵌套字段使用紧凑 JSON 字符串。
- Public IDs are newly generated and cannot be joined back to internal source-case IDs. / 公开 ID 为重新生成的匿名 ID，不能回连内部病例编号。

## Fields / 字段

| Field | 中文名称 | Type | Allowed values or format | Description |
|---|---|---|---|---|
| `id` | 公开条目ID | string | `CCHARD-PUB-XXXX` | Unique pseudonymous release identifier. / 唯一匿名发布标识。 |
| `dimension` | 能力维度 | string | `basic_knowledge`, `scenario_decision`, `evidence_reasoning`, `clinical_execution` | CCHard capability dimension. / CCHard 能力维度。 |
| `subtask` | 子任务 | string | `T01`–`T12` identifiers | CCHard subtask identifier; this release includes T05, T07, T08, T10 and T12 only. / 本版本仅纳入 T05、T07、T08、T10、T12。 |
| `specialty` | 临床专科 | string | Reviewed specialty label | Specialty retained at a broad, non-identifying level. / 经人工确认的宽泛专科标签。 |
| `difficulty` | 难度 | string | `Expert-Hard`, `Model-Hard` | Public difficulty tier. / 公开难度层级。 |
| `stem` | 临床情景 | string | De-identified and clinically equivalent rewrite | Team-authored rewrite of a case-derived scenario, not source text. / 真实病例衍生、团队重新撰写的临床等价情景，不含源文原句。 |
| `question` | 任务问题 | string | Non-empty text | Task instruction. / 任务指令。 |
| `options` | 选项 | object, array or null | JSON or `null` | This release contains open-ended tasks, therefore the value is `null`. / 本版本均为开放题，取值为 `null`。 |
| `reference_answer` | 参考答案 | object | Task-specific JSON | Team-reviewed structured answer; not a verbatim internal gold file. / 经修订的结构化参考答案，不逐字复制内部 gold。 |
| `rubric` | 评分标准 | object | 0–100 scale | Criteria, points and critical errors. / 评分维度、分值及关键错误。 |
| `source_type` | 来源类型 | string | `team_authored`, `synthetic` | Only these two values are publishable. This release uses `team_authored`. / 仅这两类允许发布；本版本均为 `team_authored`。 |
| `deid_applied` | 已执行脱敏 | boolean | `true` | Must be `true` for public items. / 公开条目必须为 `true`。 |
| `deid_checklist` | 脱敏清单 | object | Five booleans, all `true` | `no_name`, `no_identifier`, `no_exact_date`, `no_institution`, `no_copyright_source_text`. |
| `notes` | 备注 | string | Release-safe text | Public processing note without internal IDs or source excerpts. / 不含内部编号或源文片段的处理说明。 |

## Task-specific reference-answer shapes / 不同任务参考答案结构

- T05: `diagnoses[]` with rank, name and certainty.
- T07: `diagnoses[]` with grouped evidence.
- T08: `differentials[]` with supporting and opposing evidence; maximum 3.
- T10: `recommended_tests[]` with rank, test and purpose.
- T12: `treatment_plan[]` with priority, category and content.

