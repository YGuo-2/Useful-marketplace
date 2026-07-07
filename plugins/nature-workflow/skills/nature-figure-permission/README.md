# `nature-figure-permission` 技能

`nature-figure-permission` 用于在投稿前对手稿中所有图片、表格、改绘图、引用图、示意图、
Graphical Abstract、TOC 图和补充图表做版权状态核查，并准备授权申请材料。最终以 Word `.docx`
形式交付，CSV / Markdown 仅作支撑工作文件。

该技能是 `nature-orchestrator` 综述流程中的一个原子步骤（`permission: 图片版权核查`）：
orchestrator 会 `start` 这一步，本技能执行核查并产出交付文件，随后 orchestrator 用
`complete --evidence <.docx 路径>` 记录证据。技能不做流程调度，也不实现其它 skill 的逻辑。

## 功能

- 建立全文视觉素材清单（正文图/表、Graphical Abstract、TOC 图、补充图表、其它视觉素材），并编号。
- 将每一项归入 8 类分型：原创图 / 自绘机制图 / 改绘图（adapted）/ 复用图（reproduced）/
  部分复用图 / 复用改编表 / 截图网图 / AI 生成图。
- 对非原创项采集来源信息：文章、作者、期刊、出版社、年份、DOI、原图编号、版权声明、许可类型。
- 按权限判定规则给出每一项的授权判定，并联网核验目标期刊与来源出版社的图表政策。
- 逐一核查开放获取图的具体许可（CC BY / CC BY-NC / CC BY-NC-ND），无 license 一律标“需要人工核查”。
- 设定权限状态与版权风险四档（高 / 中 / 低 / 需要人工核查）。
- 为需授权项整理 RightsLink / Copyright Clearance Center 申请信息表，并填写英文授权申请邮件模板。
- 给出图注/表注版权标注建议，并对风险项给出处理建议（申请 / 重绘 / 删换 / 转文字 / 换开放许可来源）。

## 来源基础

融合自 SCI 工作流 `17-SCI图片引用权限申请器`，保留其硬规则：8 类图表分型、权限判定规则、
两套英文授权申请邮件模板（复用图 / 改绘图）、版权风险四档，以及“图片版权核查表 / 权限申请信息表 /
邮件模板 / 版权风险清单 / 图注版权标注建议 + Word 交付”产物族。

去掉了 SCI 版里与线性流程强耦合的部分（固定读取第 16/10 步输入、开场自我介绍、生成
输入/输出/过程记录/质量核查目录、下一步固定进入 18-Cover Letter）——这些交由
`nature-orchestrator` 的状态引擎负责，本技能只承担图片版权核查这一原子步骤。

图片版权与授权要求随出版社政策变化，动态信息（期刊图表政策、许可条款、授权要求）必须联网核验，
不得凭记忆判断。参见 `static/core/stance.md` 的 Mandatory online verification 一节。

## 文件结构

采用 router/static 结构：`SKILL.md` 负责短路由，`manifest.yaml` 决定常驻加载内容。本技能是
线性工作流，没有内容轴，全部领域逻辑放在常驻 core 里。

```text
nature-figure-permission/
├── SKILL.md                     # 短路由（被 orchestrator 委托的原子步骤）
├── manifest.yaml                # always_load: 共享 ethics + 本地 core
├── README.md
└── static/
    └── core/                    # 始终加载
        ├── stance.md            # 立场、联网核验、来源层级、Prohibited Actions 红线
        ├── workflow.md          # 清单→8类分型→采集来源→授权判定→风险→申请材料→交付
        └── output-contract.md   # 产物清单、.docx 主交付规则、CSV 列、邮件模板、风险四档、图注标注
```

`../_shared/core/ethics.md`（引用 / AI / 图像伦理红线）也在 `always_load` 中。

## 核心规则表

| 规则 | 说明 |
|------|------|
| 8 类分型 | 原创 / 自绘机制图 / 改绘 / 复用 / 部分复用 / 复用改编表 / 截图网图 / AI 生成图，每项归一类 |
| 原创判定 | 通常免第三方授权，但仍需核查嵌入的第三方 logo、地图、临床图、数据库截图 |
| 改绘判定 | 建议 `Adapted from…`，但最终措辞以授权要求为准，改绘不自动免除授权 |
| 复用判定 | 通常需要授权，除非许可明确允许且目标期刊接受该用途 |
| 开放获取 | 逐一核验具体许可；CC BY 多可署名复用，CC BY-NC / CC BY-NC-ND 及自定义许可须谨慎核查 |
| 无 license | 一律不假定可用，标 `需要人工核查` |
| 就严执行 | 来源出版社与目标期刊要求不一致时，按更严的一方执行 |
| 联网核验 | 期刊/出版社图表政策、许可条款、授权要求必须联网核验，不得凭记忆 |
| 不可核实 | 缺失或无法确认的来源/许可/授权状态标 `需要人工核查`，不得编造 |
| 主交付 | 最终主交付为 `.docx`；CSV / Markdown 仅作支撑，不得当作最终交付 |
| 安全红线 | 见 `stance.md` 的 Prohibited Actions：禁把来源不清判为免授权、禁凭记忆判出版社政策、禁编造授权状态/邮件回复、禁把第三方图当原创、禁用 AI 伪造研究/临床/显微图 |

## 状态

Beta。当前行为由 SCI 17 的硬规则与合成模板定义。经真实投稿授权流程验证后再考虑提升到 Stable。
