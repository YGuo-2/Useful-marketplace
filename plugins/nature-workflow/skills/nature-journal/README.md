# `nature-journal` 技能

`nature-journal` 用于在完整初稿形成后，为一篇 Nature 系列稿件分梯队筛选目标投稿期刊；用户确认目标期刊后，再深度学习该刊近 3-5 年高质量文章的写作风格与硬性投稿要求，形成投稿适配标准。

这是 `nature-orchestrator` 委托调用的**原子决策步**：orchestrator 会 `start` 本步，拿到你的产物后 `complete --evidence <产物路径>`。选刊阶段是**决策岔口**——你产出多梯队候选，orchestrator 按 decision 协议呈现给用户，用户确认后你再进入深度学习阶段。

## 功能

- 从完整初稿提取稿件画像：题目、方向、关键词、学科、目标读者、文体、创新点、证据强度、图表完整度、投稿风险。
- 用 Journal Finder / Springer Suggester / Wiley Finder / JANE / LetPub / MedSci 等工具做初步匹配。
- 对每本候选期刊逐项联网核实：范围是否匹配、是否接收该文体、收录状态、JCR 分区、中科院分区、影响因子、CiteScore、出版社、是否 OA、APC、审稿周期、年发文量、近期同题工作。
- 按 14 维、0-5 打分评估匹配度。
- 用 13 项投稿风险清单排查，高风险期刊不得作首推。
- 按四梯队策略分层：Tier 1 冲刺 / Tier 2 主投 / Tier 3 稳妥 / Backup 保底。
- 用户确认目标期刊后，检索该刊近 3-5 年高质量对标文章并按相关性排序。
- 从 8 个维度深度学习期刊风格，并逐项核对硬性投稿要求，产出适配清单。

## 来源基础

本技能融合自 SCI 从 0-1 工作流的两个步骤：

- **14-SCI目标期刊选择器**（阶段 2 选刊）：分梯队候选、14 维打分、13 项风险清单、强制联网核验、四梯队策略。
- **15-SCI目标期刊深度学习器**（阶段 2 期刊学习）：8 维风格学习、硬性投稿要求核查、稿件与目标期刊差距比对。

期刊信息具有时效性。分区、影响因子、CiteScore、APC、审稿周期、收录状态、是否接收该文体等动态信息必须联网核验，不得凭记忆；无法确认的项一律标 `需要人工核查`。核验优先级：Journal Finder 类工具先匹配，再用期刊官网 / Author Guidelines / WoS Master Journal List / JCR / 中科院分区表 / Scopus·CiteScore / DOAJ / 出版社页面逐项确认。

## 文件结构

该技能采用 router/static-dynamic 结构：`SKILL.md` 负责短路由，`manifest.yaml` 决定常驻 core 与按需 references。`nature-journal` 是线性决策工作流，没有内容轴，全部领域逻辑放在 core。

```text
nature-journal/
├── SKILL.md                     # 短路由（被 orchestrator 委托的原子步）
├── manifest.yaml                # always_load core + 共享 ethics + 按需 references
├── README.md
└── static/
    └── core/                    # 始终加载
        ├── stance.md            # 立场、强制联网核验、来源层级、红线/禁止事项
        ├── workflow.md          # 选刊 8 步 + 深度学习 4 步，每步含产物
        └── output-contract.md   # 产物清单、字段规范、报告模板、evidence 路径格式
```

## 核心规则表

| 规则 | 说明 |
|---|---|
| 强制联网核验 | 分区/IF/CiteScore/APC/周期/收录/是否接收该文体必须联网确认，禁凭记忆 |
| 匹配优先级 | 先用 Journal Finder 类工具匹配，再用官网/JCR/中科院分区/Scopus/DOAJ 逐项核实 |
| 14 维打分 | 主题、学科、读者、是否接收该文体等 14 维，0-5 分 |
| 13 项风险 | 范围不符/不收该文体/邀稿制/分区不符/APC 过高/周期过长/预警名单/掠夺性等 |
| 四梯队策略 | Tier 1 冲刺 / Tier 2 主投 / Tier 3 稳妥 / Backup 保底 |
| 高风险不首推 | 任一高风险项命中的期刊不得作为首推 |
| 决策岔口 | 只产出多梯队候选交 orchestrator 呈现，不代用户拍板 |
| 8 维风格学习 | 标题/摘要/引言/正文结构/图表/参考文献/语言/投稿文件 |
| 硬性要求核查 | 字数/摘要字数/图表数/参考文献格式/Graphical Abstract/Highlights 等逐项核对 |
| 不编造 | 不编造 IF/分区/APC/ISSN/链接/对标文章；不确定项标 `需要人工核查` |
| 合法获取 | 不用 Sci-Hub/盗版/绕过付费墙获取对标 PDF，提示用户合法下载 |

## 产物

- 选刊阶段：`目标期刊候选表.csv`、`目标期刊推荐报告.md`、`投稿风险核查.md`、`期刊信息来源记录.md`。
- 深度学习阶段：`对标文献清单.csv`、`作者指南核查表.csv`、`目标期刊适配学习报告.md`、`投稿格式适配清单.md`。

产物均为 `.md` / `.csv`，无需 docx。返回时把产物绝对路径列在最前，供 orchestrator 作 evidence 记录。
