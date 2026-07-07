# Output contract

## Deliverable

One Markdown file (no docx). Suggested name: `选题与研究空白.md`, written to the run's working / output
directory. Return its **absolute path** so nature-orchestrator can run
`complete <task_id> --evidence <path>`.

## Required structure

The file must contain these sections, in this order:

```markdown
## RIS 年份-标题-摘要分析

| 聚类 | 年份趋势 | 代表性标题/摘要模式 | 主题信号 | 可能研究空白 | 证据风险 | 需要人工核查 |
|---|---|---|---|---|---|---|

## 候选选题

| 选项 | 中文选题 | 英文题目草案 | 专业化结构 | 来源文献模式 | 具体研究空白 | 证据风险 | 创新性 | 写作难度 | 目标分区匹配 |
|---|---|---|---|---|---|---|---|---|---|
| A |  |  |  |  |  |  |  |  |  |
| B |  |  |  |  |  |  |  |  |  |
| C |  |  |  |  |  |  |  |  |  |

推荐选项：<A/B/C + 一句理由>

## 请确认选题（供 orchestrator 决策）

- A：稳妥型方案 — easiest to support and finish.
- B：平衡型方案 — balances novelty, feasibility, and target-partition fit.
- C：高冲击力方案 — sharper frontier angle, higher evidence and writing burden.
- D：自定义方案 — the user modifies A/B/C or provides a new topic.

## 最终选题记录

- 用户选择：
- 最终中文选题：
- 英文题目草案：
- 核心研究空白：
- 当前阶段：nature-topic（选题与研究空白识别）
```

## Rules on the deliverable

- Every candidate follows the fixed pattern `研究对象 + 核心机制/关键变量 + 临床或科学问题 + 综述视角` and
  fills all five required fields.
- No broad / vague titles (anti-example `肠道菌群与肿瘤免疫治疗研究进展`).
- No invented papers, authors, DOI, PMID, journal statistics, or citation counts; clusters are aggregate
  descriptions of the export.
- Leave the `最终选题记录` fields blank / `待用户确认` until the decision is made — this step emits
  candidates, it does not decide.
- Mark any unverifiable metadata `需要人工核查`. Do not state a final included-study count.
- Return the absolute artifact path as the last line of the report so it can be used directly as evidence.
