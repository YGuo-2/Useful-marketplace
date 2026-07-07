# `nature-cover-letter` 技能

`nature-cover-letter` 用于为一篇即将投稿的稿件撰写针对目标期刊定制的 Cover Letter（投稿信），
最终以 Word `.docx` 形式交付，并附带投稿声明核查表。它是 `nature-orchestrator` 编排流程中的一个
原子步骤（review 模板第 12 步 `coverletter`）：orchestrator 会 `start` 该步、把润色稿与目标期刊
上下文交给本技能，拿到 `Cover_Letter.docx` 后用 `complete --evidence <路径>` 收尾。

该技能支持中文输入：用户可以说“写投稿信”“Cover Letter 撰写”“投稿附信”“投稿声明核查”等；技能用
英文撰写正式投稿信，同时用中文给出说明和需用户确认清单。

## 功能

- 基于深度润色稿、目标期刊深度学习/选刊结果、图片权限核查状态，撰写目标期刊定制的投稿信（非通用模板）。
- 固定七段结构：称呼 / 投稿声明 / 研究背景与必要性 / 核心内容与创新 / 期刊契合度 / 投稿声明集合 /
  结尾（含通讯作者占位）。
- 完成 9 项投稿声明核查：原创性、未一稿多投、利益冲突、基金、伦理、数据可用性、AI 使用、图表版权授权、
  推荐审稿人。
- 只使用项目已确认信息；缺失信息一律用占位符或 `需要用户确认` 标记，绝不编造。
- 联网核验目标期刊最新的 Cover Letter 要求（作者指南、投稿系统字段、声明要求）；无法确认的标
  `需要人工核查`。
- 输出正式 Word 投稿信 `Cover_Letter.docx`，以及中文说明、声明核查表、需用户确认清单、质量核查记录。

## 来源基础

- 融合自 SCI 0-1 workflow 第 18 步「Cover Letter 撰写器」，抽取其硬规则：七段结构、9 项声明核查、
  Word `.docx` 为最终交付、禁止编造与夸大、不得把综述包装成原创研究、不得隐瞒图片授权风险。
- 目标期刊 Author Guidelines / Instructions for Authors 与投稿系统 Cover Letter 字段要求。
- 出版商关于伦理、AI 使用、利益冲突、基金、数据可用性、图表授权、推荐审稿人的声明要求。
- 项目内的润色稿、目标期刊学习/选刊报告、图片权限核查结果。
- 共享伦理红线 `../_shared/core/ethics.md`（不编造引用/数据/授权，联网核验动态信息）。

## 文件结构

该技能采用 router/static-dynamic 结构：`SKILL.md` 负责短路由，`manifest.yaml` 决定常驻 core。
`nature-cover-letter` 是线性工作流，没有内容轴，全部领域逻辑在 `static/core/` 三个文件中。

```text
nature-cover-letter/
├── SKILL.md                     # 短路由（说明本技能是 orchestrator 委托的原子步）
├── manifest.yaml                # always_load core + 共享伦理红线
├── README.md
└── static/
    └── core/                    # 始终加载
        ├── stance.md            # 立场 + 红线（禁止编造/夸大/隐瞒授权风险）
        ├── workflow.md          # 输入类型、10 步工作流、输出格式
        └── output-contract.md   # 交付清单、七段结构、9 项声明核查、Word 交付要求
```

## 核心规则

| 规则 | 说明 |
|---|---|
| 定制而非模板 | 投稿信必须贴合目标期刊的 aims/scope/读者/文章类型与特殊要求 |
| 只用确认信息 | 缺失的作者/单位/通讯/基金/伦理/利益冲突/数据/AI/图表授权一律占位或标 `需要用户确认` |
| 不编造 | 不编造文献/DOI/PMID/作者/期刊指标/授权状态；不可核实项标 `需要人工核查` |
| 联网核验动态信息 | 期刊范围/IF/分区/APC/投稿规则/许可/Cover Letter 要求必须联网核验，不凭记忆 |
| 不夸大 | 不用 first/only/breakthrough（除非材料明确支持）；不把综述包装成原创研究发现 |
| 不隐瞒风险 | 图片/图表授权未解决的风险必须如实呈现，不得隐藏 |
| 七段结构 | 称呼 / 投稿声明 / 背景与必要性 / 核心内容与创新 / 期刊契合度 / 投稿声明集合 / 结尾 |
| 9 项声明核查 | 原创性 / 未一稿多投 / 利益冲突 / 基金 / 伦理 / 数据可用性 / AI 使用 / 图表版权 / 推荐审稿人 |
| Word 为交付 | 最终主交付是 `Cover_Letter.docx`；Markdown 仅作支撑草稿 |
| 不操作投稿系统 | 本步只写信；投稿系统操作交给后续 `submit` 投稿指导步骤 |

## 交付与状态

- 主交付：`Cover_Letter.docx`（作为该步 evidence 路径）+ `投稿声明核查表.md`。
- 支撑：`Cover_Letter.md`、`Cover_Letter_中文说明.md`、`需用户确认信息清单.md`、
  `Cover_Letter质量核查.md`、`Word交付内容核查表.csv`。
- 包状态：`ready_to_submit` / `draft_with_placeholders` / `needs_user_confirmation` / `blocked`。

## 状态

Alpha（v0.1.0）。骨架与 SCI 第 18 步硬规则已就位；正式行为需在真实投稿项目与目标期刊要求核验后再稳定化。
