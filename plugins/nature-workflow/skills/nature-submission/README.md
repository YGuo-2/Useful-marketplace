# `nature-submission` 技能

`nature-submission` 用于在手稿、图表、Cover Letter、声明文件和图片授权基本就绪后，整理最终投稿材料，
规划文件命名与上传顺序，给出投稿系统字段填写建议，核查缺失材料与投稿风险，并输出一份 Word 投稿指导交付
文件，逐步引导作者在目标期刊投稿系统里完成提交。

该技能是 `nature-orchestrator` 编排流程中的一个**原子步骤**：orchestrator 会 `start` 本步，拿到交付
文件后用 `complete --evidence <交付文件路径>` 收尾。因此工作流会明确给出可当 evidence 的 `.docx` 绝对
路径。

该技能支持中文输入。用户可以直接说“投稿指导”“投稿材料准备”“投稿清单”“上传顺序”“投稿前检查”“最终提交前
确认”“投稿后记录”等；技能默认返回中文说明与提醒，同时按期刊要求准备英文字段内容。

## 功能

- 覆盖完整材料集：Main Manuscript、Title Page、Cover Letter、Figures、Tables、Graphical Abstract、
  Highlights、Supplementary Materials、Declarations / 利益冲突、Funding、Data Availability、
  AI Use Statement、Figure Permission、Suggested / Opposed Reviewers。
- 为每项材料标注状态：已完成 / 需格式调整 / 需用户确认 / 缺失 / 不适用。
- 规划清晰、英文、无问题字符、投稿系统兼容的文件命名，并给出示例。
- 规划投稿系统上传顺序，并把每个文件映射到对应栏目。
- 生成投稿系统字段填写建议（Title、Abstract、Keywords、通讯作者、声明、推荐审稿人等）。
- 核查缺失材料与投稿前风险（授权未解决、格式不符、字数超限、参考文献风格未适配、APC/OA 未确认等）。
- 生成带 checkbox 的最终提交前确认清单，以及投稿后记录模板。
- 强制联网核验目标期刊的最新投稿系统与作者指南，无法核实项标 `需要人工核查`。

## 来源基础

本技能融合自 SCI 从 0-1 工作流的**阶段 2 / 第 19 步「SCI 投稿指导器」**
（`SCI从0-1workflow/skills/19-SCI投稿指导器/`），将其投稿材料清单、文件命名规范、上传顺序、投稿系统
字段建议、缺失/风险核查、提交前确认清单和投稿后记录模板等硬规则迁移到 nature-workflow 的 router /
static-dynamic 骨架，并强化了投稿系统安全红线。

规则依据：

- 目标期刊 Author Guidelines / Submission Guidelines 与投稿系统页面。
- 出版商（Nature Portfolio / Springer Nature 及目标出版商）稿件准备与政策页面。
- 用户本地的手稿、Cover Letter、声明与授权材料。
- 动态信息（期刊范围、IF、分区、APC、投稿规则、许可）必须投稿时联网核验，不得凭记忆。

## 文件结构

该技能采用 router/static-dynamic 结构：`SKILL.md` 负责短路由，`manifest.yaml` 决定常驻加载内容。
`nature-submission` 是线性工作流，没有内容轴，全部领域逻辑放在三个 core 文件里。

```text
nature-submission/
├── SKILL.md                     # 短路由（英文），被 nature-orchestrator 委托
├── manifest.yaml                # always_load core + 共享 ethics 红线
├── README.md                    # 本文档（中文）
└── static/
    └── core/                    # 始终加载
        ├── stance.md            # 立场 + 投稿系统安全红线 + 禁止事项 + 联网核验 + 来源层级
        ├── workflow.md          # 编号工作流 + 每步产物 + 编排交接
        └── output-contract.md   # 交付清单、文件命名、提交前确认清单、交付格式
```

`manifest.yaml` 的 `always_load` 还包含 `../_shared/core/ethics.md`（引用、署名与 AI 使用红线）。

## 核心规则

| 类别 | 规则 |
|---|---|
| 材料覆盖 | 必须覆盖 Main Manuscript / Title Page / Cover Letter / Figures / Tables / Graphical Abstract / Highlights / Supplementary / Declaration / Funding / Data Availability / AI Use / Figure Permission / Suggested-Opposed Reviewers |
| 状态标注 | 每项材料标 已完成 / 需格式调整 / 需用户确认 / 缺失 / 不适用 |
| 文件命名 | 清晰、英文、无空格与问题字符（`/ \ : * ? " < > \|`）、投稿系统兼容，给示例 |
| 联网核验 | 投稿系统与作者指南必须联网核验并记录访问日期；无法核实标 `需要人工核查` |
| 不编造 | 不编造作者信息、基金、伦理、声明、期刊指标、授权状态、DOI/PMID、字段规则 |
| 安全红线（最关键） | 绝不索取或保存账号密码；不绕验证码/双因子/机构认证；不代替确认付款/版权转让/法律声明；用户最终确认前不点 Submit |
| 交付格式 | 主交付为 `.docx`；Markdown 仅作支撑；不得把 Markdown 当最终交付 |
| 编排交接 | 返回 `投稿指导交付文件.docx` 的绝对路径作为 evidence；无法完成则报告 blocker |

## 交付物

- 主交付：`投稿指导交付文件.docx`（evidence 文件）。
- 支撑文件：`投稿材料清单.md`、`投稿步骤指导.md`、`投稿系统字段填写建议.md`、`缺失材料与风险清单.md`、
  `最终提交前确认清单.md`、`投稿后记录.md`。

## 注意事项

- 本技能是**投稿辅助**，不是代投稿：登录、验证码、认证、付款、版权转让、法律声明与最终 Submit 由用户本人完成。
- 清单填满不等于“已投稿/可提交”；提交前必须由用户逐页人工检查。
- 上游材料（终稿、Cover Letter、图片授权核查）缺失时，路由回对应步骤，不得编造。
