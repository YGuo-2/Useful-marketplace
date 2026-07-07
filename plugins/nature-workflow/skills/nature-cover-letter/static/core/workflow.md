# Workflow and output format

## Accepted inputs

The skill may receive: the deep-polished manuscript (`.docx` and/or Markdown backup); the
polish change notes and target-journal adaptation check table; the figure-permission check
outputs (permission table, copyright-risk list, caption-attribution notes); the target-journal
study/style-learning report and author-guidelines check table; the journal selection /
recommendation report; the manuscript title, article type, keywords, abstract, and main
novelty; the author list, affiliations, corresponding author, email, and ORCID if provided;
funding, conflict-of-interest, ethics, data-availability, AI-use, and author-contribution
statements if provided; whether the journal requires special Cover Letter statements or
suggested reviewers; and the target journal name, publisher, and submission/author-guidelines
links.

If the deep-polished manuscript is missing, or figure-permission status has not been checked,
say so and route back to the owning upstream step rather than inventing the missing material.
If any author or declaration information is missing, do not fabricate it — mark it
`需要用户确认`.

## Workflow

1. Confirm task mode and input readiness: `draft`, `audit`, or `revise`. Inventory the inputs
   above and state which are present.
   - Product: input inventory + readiness note.
2. Verify the target journal's current Cover Letter requirements online — author guidelines,
   submission-system Cover Letter fields, and publisher requirements for declarations (ethics,
   AI use, conflict of interest, funding, data availability, figure permissions) and for
   suggested/opposed reviewers. Anything not confirmable is marked `需要人工核查`.
   - Product: target-journal Cover Letter requirement notes with source URLs.
3. Extract the manuscript facts the letter needs: title, article type, target journal, research
   field, review scope, key novelty, main contribution, target readership, and fit with the
   journal's aims and scope.
   - Product: manuscript fact sheet.
4. Extract the nine submission-declaration items (see `output-contract.md`): originality; not
   under consideration elsewhere; conflict of interest; funding; ethics; data availability;
   AI use; figure/table copyright/permission; suggested reviewers. Mark each as confirmed,
   missing, or not-applicable, with its source.
   - Product: declaration source table.
5. Build the user-confirmation list for every missing or unconfirmed item.
   - Product: `需用户确认信息清单.md`.
6. Draft the seven-paragraph English Cover Letter (structure in `output-contract.md`) using only
   confirmed facts; use placeholders or `需要用户确认` for the rest; keep it target-journal
   specific and do not overstate contribution.
   - Product: `Cover_Letter.md` (working draft).
7. Produce the Chinese explanation: the role of each paragraph and where user confirmation is
   needed.
   - Product: `Cover_Letter_中文说明.md`.
8. Fill the nine-item submission-declaration checklist.
   - Product: `投稿声明核查表.md`.
9. Run QA: no fabricated author/declaration/permission facts; no exaggeration; no "first/only/
   breakthrough" without support; review not framed as original research; permission risks
   surfaced; letter is journal-specific; all declarations checked; all gaps marked.
   - Product: `Cover_Letter质量核查.md`.
10. Render the final Word deliverable `Cover_Letter.docx` from the confirmed draft (Markdown is
    support only), plus a Word delivery-content check table.
    - Product: `Cover_Letter.docx` (the evidence path) + `Word交付内容核查表.csv`.

## Output format

Unless the user asks for another format, return:

```text
投稿信交付
- Cover_Letter.docx: [absolute path]   ← 正式交付（作为该步 evidence）
- 投稿声明核查表: [absolute path]
- 需用户确认信息清单: [absolute path]

投稿信息
- 目标期刊 / 文章类型 / 稿件题目 / 通讯作者信息状态:

七段结构摘要
- 称呼 / 投稿声明 / 研究背景与必要性 / 核心内容与创新 / 期刊契合度 / 投稿声明集合 / 结尾:

投稿声明核查（9 项）
- 原创性 / 未一稿多投 / 利益冲突 / 基金 / 伦理 / 数据可用性 / AI 使用 / 图表版权 / 推荐审稿人:

需要用户确认
- [author/affiliation/corresponding author, funding/ethics/COI/data, figure permission, AI use,
  journal-specific requirements, or "None"]

风险与缺口
- [unresolved permission risk, unverifiable journal requirement (需要人工核查), missing input, ...]

包状态
- ready_to_submit / draft_with_placeholders / needs_user_confirmation / blocked
```
