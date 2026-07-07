# Output Contract

## Deliverables

A benchmark job produces these artifacts (no DOCX — the deliverables are a RIS library plus Markdown/CSV
reports):

- `输出/对标综述文献库RIS/对标综述文献库.ris` (plus per-item RIS when useful) — the benchmark review library;
- `输出/对标综述排序表.csv` — the ranking table;
- `输出/对标综述筛选理由.md` — the selection rationale;
- `输出/Zotero导入记录.md` — the import result and which fallback rung was used;
- `输出/对标综述PDF状态表.csv` — per-review PDF acquisition status;
- `输出/对标综述整理素材库.md` — reusable structural/writing material, only when full-text PDFs were read;
- `输出/对标综述深度学习报告.md` — the deep-learning report (**evidence: benchmark-corpus report**);
- `输出/拟定标题与写作思路.md` — proposed title direction and writing framework;
- `输出/下一步文献分类指导框架.md` — the downstream classification guide (**evidence: classification guide**).

The RIS library and the CSV tables are the structured source of truth; the Markdown reports are the
human-facing learning and handoff.

## Evidence for the orchestrator

The orchestrator's review-genre step `benchmark` records **benchmark-corpus report + classification guide**.
Return both absolute paths explicitly:

- benchmark-corpus report → `输出/对标综述深度学习报告.md`;
- classification guide → `输出/下一步文献分类指导框架.md`.

## Required traceability

- The corpus is built from the upstream screened library and the confirmed topic, not a fresh unscoped
  search.
- The reviews are ranked by topical fit first, then journal/article quality; every used metric is verified
  or marked `需要人工核查`.
- Every RIS record preserves real metadata; missing fields are blank or marked `缺失/需要人工核查`.
- The Zotero import ladder (plugin/connector → Computer Use → manual prompt) is recorded with the reason for
  each fallback.
- Full-text learning covers only PDFs the user actually obtained; the PDF status table matches what was
  read.

## User-facing report

Report in the user's language:

```markdown
## 对标综述库建立结果
- 候选综述数量 / 最终纳入数量（不足 10 篇时注明原因）：
- 排名第一的对标综述：
- 对标综述文献库 RIS：<absolute path>
- Zotero 导入状态（插件/连接器 / Computer Use / 手动）：
- PDF 获取状态：

## 对标综述排序
| 排名 | 标题 | 期刊 | 年份 | DOI/PMID | 匹配理由 | 期刊/文章质量依据 | PDF状态 |
|---:|---|---|---:|---|---|---|---|

## 深度学习结论
- 可借鉴的标题方向 / 推荐写作框架 / 推荐写作思路：
- 推荐图表策略 / 正文与图片关系 / 写作风格建议：
- 争议与研究空白呈现方式：

## 交接给下一步文献分类
- 建议的二级分类 / 三级分类 / 分类理由：
- 需要人工核查：

## 交付物路径（可作为 evidence）
- 对标综述深度学习报告：<absolute path>
- 下一步文献分类指导框架：<absolute path>
```

## Quality gates

Before handoff, all of the following must hold:

- selection is based on the upstream library and confirmed topic, ranked by topical fit then
  journal/article quality;
- used journal metrics are verified, or marked `需要人工核查`;
- the `对标综述文献库RIS` folder exists and contains the selected references;
- the user was reminded to open and keep Zotero open, and the plugin/connector was attempted before any
  fallback;
- the user was told to reply after full or partial PDF acquisition, and only obtained PDFs were read at the
  full-text level;
- the deep-learning report covers framework, writing logic, style, figure layout, and figure-text
  relationship;
- a proposed title, writing idea, and classification guidance were produced;
- no fabricated bibliographic field or metric, no copied content, and no illegal PDF route were used.

## Delivery note

State that journal metrics and any `需要人工核查` items require human verification, and that the corpus is a
learning reference for planning and classification — its structure and strategy may be learned, but no title,
section, prose, figure, or viewpoint may be copied.
