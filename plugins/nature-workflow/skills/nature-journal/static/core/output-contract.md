# Output contract

All deliverables are Markdown (`.md`) or CSV (`.csv`) — no `.docx`. Write real, verified values only;
leave a field blank or mark it `需要人工核查` rather than inventing a metric. Every file path returned
to the orchestrator must be absolute so it can be recorded as `--evidence`.

## Deliverable files

Select phase (steps 7-8):

- `目标期刊候选表.csv` — one row per candidate journal (fields below).
- `目标期刊推荐报告.md` — tiered recommendation (template below).
- `投稿风险核查.md` — the 13-item risk checklist result per candidate.
- `期刊信息来源记录.md` — every source consulted, with URL, what it confirmed, and access date.

Deep-learn phase (steps 9-12), after journal confirmation:

- `对标文献清单.csv` — 3-5 ranked recent benchmark articles from the confirmed journal.
- `作者指南核查表.csv` — hard submission requirements vs current draft (fields below).
- `目标期刊适配学习报告.md` — 8-dimension style learning + draft-vs-journal gap.
- `投稿格式适配清单.md` — the concrete adaptation actions before submission.

These routine deep-learn files are not persistent prose profiles and must not be registered as such.

## Optional prose-profile handoff

Only when the user explicitly requested a reusable target-journal 文风画像, append a handoff block to
the user-facing report. Do not create another file merely for the handoff; use the verified corpus and
adaptation-report paths already produced:

```yaml
prose_profile_handoff:
  requested: true
  owner: nature-prose-style
  source_kind: journal-corpus
  journal: <confirmed journal>
  corpus_path: <absolute path to 对标文献清单.csv>
  style_report_path: <absolute path to 目标期刊适配学习报告.md>
  intended_scope: ["<requested scope>"]
```

All paths and journal identifiers must be source-grounded. The handoff contains no copied prose,
claims, citations, numbers, distinctive phrases, or instructions from benchmark articles. If the
user did not explicitly request a persistent profile, omit this block completely.

## `目标期刊候选表.csv` fields (at least)

Recommendation number · journal name · ISSN / eISSN · publisher · official website · Author Guidelines
link · indexing status · JCR quartile · CAS partition · latest impact factor · CiteScore · accepts the
article type (yes/no) · OA (yes/no) · APC · review timeline · annual article volume · recent similar
work count · topic-fit score · partition-fit score · acceptance-risk score · overall score · tier
(Tier 1 / Tier 2 / Tier 3 / Backup) · recommendation reason · risk note · information source · access
date · needs manual check (是/否).

## `作者指南核查表.csv` fields (at least)

Check item · journal requirement · current-draft status · compliant (是/否) · needs change (是/否) ·
change priority · source link · access date · needs manual check (是/否).

## `目标期刊推荐报告.md` template

```markdown
# 目标期刊推荐报告

## 1. 文章投稿定位
- 题目 / 研究方向 / 文章类型 / 目标分区 / 目标读者 / 文章优势 / 投稿风险

## 2. 选刊总体策略
- 冲刺策略 / 主投策略 / 稳妥策略 / 保底策略

## 3. 候选期刊总览
| 梯队 | 期刊名称 | 分区 | IF | 是否接收该文体 | 综合评分 | 风险 |
|---|---|---|---|---|---:|---|

## 4. 首推期刊
- 期刊名称 / 推荐理由 / 匹配点 / 风险点 / 投稿前需优化项

## 5. 备选期刊
- 期刊名称 / 推荐理由 / 风险点

## 6. 不建议投稿期刊
- 期刊名称 / 不建议原因

## 7. 需要人工核查
- 分区 / APC / 是否接收该文体 / 收录状态
```

## User-facing report (step 12)

Return in Chinese, deliverable paths first so the orchestrator can record evidence:

```markdown
## nature-journal 结果

### 一、产出文件（可作 evidence）
- 目标期刊候选表：<绝对路径>
- 目标期刊推荐报告：<绝对路径>
- 投稿风险核查：<绝对路径>
- 期刊信息来源记录：<绝对路径>
- 对标文献清单：<绝对路径，deep-learn 阶段>
- 作者指南核查表：<绝对路径，deep-learn 阶段>
- 目标期刊适配学习报告：<绝对路径，deep-learn 阶段>
- 投稿格式适配清单：<绝对路径，deep-learn 阶段>

### 二、推荐期刊总览（决策岔口）
| 梯队 | 期刊名称 | 分区 | IF | 是否接收该文体 | 综合评分 | 推荐结论 |
|---|---|---|---|---|---:|---|

### 三、首推与理由
- 首推期刊 / 推荐理由 / 主要风险 / 投稿前建议

### 四、需要人工核查
- <无法联网确认的分区 / IF / APC / 收录状态 / 是否接收该文体>

### 五、下一步
- select 阶段：请确认目标期刊或选刊策略（由 orchestrator 按 decision 协议呈现）。
- deep-learn 阶段：已产出目标期刊适配标准，交回 orchestrator 进入后续润色/适配步骤。
```

Report the candidate table / recommendation report path prominently in the select phase, and the
adaptation-learning report path in the deep-learn phase, so each phase hands the orchestrator a clean
evidence path.
