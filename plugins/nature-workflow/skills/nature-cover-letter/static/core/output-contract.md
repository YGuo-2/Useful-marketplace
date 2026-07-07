# Output contract

## Main deliverable

`Cover_Letter.docx` — a formal English Cover Letter tailored to the target journal. This is the
step's evidence path; the orchestrator `complete`s the `coverletter` step with it. Markdown
files are working support only and must not be delivered as the final letter.

The `.docx` must contain:

1. A target-journal-specific English Cover Letter (the seven paragraphs below).
2. The manuscript title and article type.
3. A journal-fit statement.
4. Review-value and novelty statements supported by project materials (not overstated).
5. The confirmed required submission declarations.
6. Placeholders or `需要用户确认` markers for missing author/declaration information.
7. Figure/table permission status when the journal requires it — including unresolved risks.

## Supporting deliverables

- `Cover_Letter.md` — Markdown backup of the letter.
- `Cover_Letter_中文说明.md` — per-paragraph role explanation and confirmation points.
- `投稿声明核查表.md` — the nine-item declaration checklist.
- `需用户确认信息清单.md` — every missing or unconfirmed item.
- `Cover_Letter质量核查.md` — the QA record.
- `Word交付内容核查表.csv` — Word delivery-content check table.

## Fixed seven-paragraph structure

The Cover Letter uses this order. Every claim must come from confirmed project material;
anything else is a placeholder.

1. **Salutation** — the editor's name if known; otherwise `Dear Editor,` or the form the target
   journal accepts.
2. **Submission statement** — state the manuscript title, the article type, and the target
   journal.
3. **Research background and need** — briefly explain why the field matters and why this review
   is timely or necessary.
4. **Core content and novelty** — summarize the review scope, structure, and main contribution;
   emphasize synthesis/framework/relevance value only as supported. Do not exaggerate and do not
   frame a review as an original research discovery.
5. **Fit with the target journal** — explain how the manuscript fits the journal's aims and
   scope and why its readership would be interested.
6. **Submission declarations** — include only confirmed declarations: originality; not under
   consideration elsewhere; conflict of interest; funding; ethics/data availability; AI use if
   required; figure/table permission status if required.
7. **Closing** — ask the editor to consider the manuscript for review; provide
   corresponding-author placeholders (name, affiliation, email).

### Reference template (Markdown draft only)

```markdown
Dear Editor,

We are pleased to submit our manuscript entitled "[Manuscript Title]" for consideration as a
[Article Type] in [Target Journal].

[Why the field matters and why this review is timely.]

[Scope, structure, and main contribution of the review — supported, not overstated.]

[Why the manuscript fits the aims, scope, and readership of the target journal.]

[Only confirmed declarations: originality; not under consideration elsewhere; conflicts of
interest; funding; ethics/data availability/AI use; figure permissions.]

Thank you for considering our manuscript. We would be grateful if it could be considered for
publication in [Target Journal].

Sincerely,
[Corresponding Author Name]
[Affiliation]
[Email]
```

## Nine-item submission-declaration checklist

Fill this table; each row is confirmed / missing / not-applicable with its source and whether the
user must confirm it. Never mark an item confirmed without project evidence.

| 声明项目 | 是否需要 | 当前状态 | 信息来源 | 是否需要用户确认 |
|---|---|---|---|---|
| 1. 原创性声明 | | | | |
| 2. 未一稿多投声明 | | | | |
| 3. 利益冲突 | | | | |
| 4. 基金声明 | | | | |
| 5. 伦理声明 | | | | |
| 6. 数据可用性 | | | | |
| 7. AI 使用声明 | | | | |
| 8. 图表版权授权 | | | | |
| 9. 推荐审稿人 | | | | |

## Package readiness

Report one state: `ready_to_submit` (all declarations confirmed, no open placeholders),
`draft_with_placeholders` (letter drafted, some confirmed fields still placeholders),
`needs_user_confirmation` (blocked on author/declaration/permission input), or `blocked`
(missing upstream deliverable such as the polished manuscript or permission check).
