# `nature-orchestrator` 技能

`nature-orchestrator` 是 nature-* 技能集的**生命周期编排层**：把一份**文体模板**展开成状态引擎里的有序任务序列，然后带用户一步步走完"从选题到投稿"的全流程，**每一步委托给拥有它的 nature-\* 技能**。

它本身不做领域工作。检索、精读、图表、撰写、润色、审稿回复都已在各 nature-* 技能里有更深的实现；本技能只负责排序与委托，绝不内联它们的提示词。

## 与 `nature-workflow` 的区别

- `nature-workflow` 是**轻量 router + 进度/记忆跟踪器**（指路 + 维护 `nature.yml`/`memory.md`）。
- `nature-orchestrator` 是**内容编排层**（把一整篇论文的步骤串成流程并逐步委托）。
- 两者靠同一个状态引擎解耦：orchestrator 复用 `nature_progress.py` 记进度，不另造一套。

## 来源基础

编排骨架、投稿尾链与文献治理步骤的领域 know-how 融合自 `SCI从0-1workflow`（21 步综述流程）。融合纪律：只搬"编排 + 领域规则"，执行步一律委托现有 nature-*，不复制其提示词实现。

## 工作方式

1. **定文体**：按 `../_shared/core/paper-type-taxonomy.md` 的 5 类判定 `paper_type`（当前提供 `review` 模板）。
2. **读模板**：从 `static/fragments/paper_type/<genre>.md` 拿到有序任务序列（每步含 id/title、委托目标、evidence 期望、是否决策岔口）。
3. **一次铺满**：调 `nature_new_workflow`（或 CLI `new --task ...`）把整串任务写进 `nature.yml`。
4. **逐步推进**：`status` 找下一步 → `start` → 委托对应技能 → 拿到产物后 `complete --evidence <路径>`；卡住 `block --reason`。
5. **进度可见**：用引擎的 `status`/`progress.md` 显示"第几步 / 下一步"，不背诵编号。

## 文件结构

```text
nature-orchestrator/
├── README.md
├── SKILL.md                         # router：编排五步协议
├── manifest.yaml                    # always_load + paper_type 轴
└── static/
    ├── core/
    │   ├── stance.md                # 编排立场：委托不重写、引擎持有真相
    │   ├── workflow.md              # 编排循环 + 确切引擎调用（CLI/MCP）
    │   └── decision.md              # 轻量决策协议（关键岔口带推荐选项）
    └── fragments/
        └── paper_type/
            └── review.md            # 综述文体模板：14 步任务序列
```

## 核心规则

| 领域 | 规则 |
|---|---|
| 委托而非重写 | 执行步交给 nature-*，只传领域参数作为任务简报 |
| 引擎持有真相 | 进度/活跃步/下一步由 `nature_progress.py` 推导，不手写状态块 |
| evidence 硬门 | 有真实产物才 `complete`，引擎强制 evidence；卡住 `block` 带原因 |
| 不编造 | 不伪造文献/DOI/PMID/期刊指标/授权状态；不可核实标 `需要人工核查` |
| 动态信息 | 期刊范围/IF/分区/APC/投稿规则由委托技能联网核验 |
| 文体通用 | review 是第一个模板；其他文体新增 `paper_type` fragment，不改 core |

## 委托映射（review 模板）

| 步骤 | 委托目标 | 现状 |
|---|---|---|
| search / read / outline / draft / figure / polish / response | nature-academic-search / -reader / -writing / -figure / -polishing / -response | 现有，直接跑 |
| topic / screen / benchmark | nature-topic / -screening / -benchmark | 阶段 3 新建 |
| journal / permission / coverletter / submit | nature-journal / -figure-permission / -cover-letter / -submission | 阶段 2 新建 |

占位步骤就绪前，可手动或通用引导完成，仍照常 `complete --evidence` 以保留可追溯性；对应技能上线后把委托目标接上即可。
