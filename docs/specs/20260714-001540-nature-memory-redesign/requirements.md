# nature-workflow 论文级记忆重设计需求规范

> **功能名称：** Paper-scoped Memory Lifecycle
> **来源设计：** `docs/specs/20260714-001540-nature-memory-redesign/design.md`
> **版本：** v1.0
> **状态：** 已批准
> **最后更新：** 2026-07-14

> **高风险变更警告：** 当前任务涉及并发写入、数据迁移、隐私边界和安全信任边界，必须进行人类深度审查，切勿草率合并。

---

## 1. 概述

本需求完全从 `design.md` 的 Low Level Design 派生。目标是保留论文级 Markdown 记忆的透明、低成本和 Git 可审计特征，同时补齐稳定身份、物理隐私边界、并发写入、生命周期、确定性召回、迁移和工作流接入。

本期不引入向量数据库、embedding、持久化 FTS/BM25 索引或外部 memory 服务。memory 是低信任项目数据，不是系统指令，也不能替代动态期刊事实的实时官方核验。

---

## 2. Analyze Requirements / 需求分析结论

- **歧义检查：** scope 专指由 `memory.md` 或 `memory.local.md` 决定的物理存储边界；lifecycle 专指 active、superseded、archived；confidence 只使用 confirmed、likely、tentative 枚举；forget 只归档且不擦除正文或 Git 历史；locator 是工具解析的稳定逻辑位置，不声称为浏览器 fragment。
- **设计一致性：** 全部需求由单文件 canonical store、稳定 UUID、workflow 锁与 ETag、实时扫描、词法 recall、application facade、物理 shared/local 和兼容迁移设计派生，没有扩大为跨项目记忆或外部数据库。
- **冲突检查：** 人类可读与机器稳定身份通过隐藏 metadata 解决；Git 审计与本地隐私通过物理分文件解决；容量与可记忆性通过 soft active budget、hard file budget 和显式 consolidation 解决；progress 与 memory 通过非原子 facade 结果解决。
- **失败路径：** 覆盖 workflow 歧义、scope 非法、local 被 Git 跟踪、schema 损坏、路径逃逸、ETag 冲突、锁超时、半写、预算超限、无召回命中、迁移碰撞、旧 sentinel 损坏、progress 已提交但 memory 失败和官方来源不可用。
- **权限 / 隐私 / 安全：** 用户可控 memory 数据不得进入高权重 AGENTS 指令；local 无法证明未跟踪且已 ignore 时 fail closed；任一 scope 拒绝明显 secret；evidence 默认不触发读取、网络或命令。
- **并发 / 数据一致性：** mutation 在 workflow 锁内重读并以 entry ETag 做 CAS；v1 不做跨 workflow/scope 双写；migrate --all 逐篇原子而非全局事务；facade 明确 progress 与 memory 非原子。
- **兼容 / 迁移：** 旧 `M<int>`、标题版、旧 timestamp 和旧工具均有读兼容或弃用 shim；读取不隐式迁移，显式迁移支持 dry-run、幂等和逐篇恢复。
- **Intake 未决项归类：** 评分权重和 soft budget 可通过版本化 fixture 校准；无词面同义召回只建立 baseline；向量、物理 archive、动态 cache 和自动语义合并均在范围外。
- **Quick Plan 跳过原因：** n/a，采用 strict Design-First。

---

## 3. Intake Handoff / 澄清交接

- **Status:** complete
- **Confirmed facts:** 用户要求先生成规范且规范批准前不写业务代码；向量数据库明确延期；当前分支含未提交的部分重设计；已验证静态 AGENTS、实时扫描、稳定 ID、workflow 锁/ETag、非向量召回和物理隐私分层可行。
- **Scope:** memory 数据模型、lifecycle/API、召回、预算、并发、迁移、MCP facade、orchestrator、AGENTS 信任边界、local/shared、测试、eval、README、hook 和 manifest。
- **Non-goals:** 向量/embedding、持久 FTS/BM25、动态标题索引、一条一文件、跨 workflow/scope 双写、程序自动生成合并正文、动态期刊事实缓存、secret vault 和批准前业务实现。
- **Decision boundaries:** 实现可在不改变外部契约和验收门槛的前提下优化内部代码；跨边界事务、隐私默认、破坏性 API、预算安全墙和验收门槛变化需要重新审批。
- **Success criteria:** 结构规范校验通过；自动化覆盖兼容、迁移、并发、注入、隐私、预算、召回和完整 Agent 工作流；检索与 Agent eval 达到本文件门槛。
- **Assumptions:** 完整实现 P0 安全基础、P1 lifecycle/API 和验收；shared/local 分别使用 `memory.md` 与 `memory.local.md`；纯词法方案不保证无词面跨语言语义召回。
- **Risks:** 当前动态 sentinel、索引覆盖、并发丢更新和隐式 workflow 选择；Git 历史不可自动擦除；中文短词和跨语言同义召回受限；memory 后处理失败不得诱导 progress 重试。

---

## 4. 功能需求与验收标准

### REQ-001: 稳定且可读的论文级记录

作为论文 workflow 的使用者，我希望记忆既能自然阅读又有不可变身份，以便跨会话更新、引用和迁移不依赖标题或行号。

#### AC-001.1 新建和改名

- **GIVEN** 一个合法 workflow 和一条新 shared 或 local 记忆
- **WHEN** 调用 remember 创建记录并随后修改显示标题
- **THEN** 工具生成的稳定 UUID 保持不变，正文可读，scope 由物理文件推导

#### AC-001.2 Metadata 约束

- **GIVEN** 一条 fact 或 hypothesis 记录
- **WHEN** 工具校验其 hidden metadata
- **THEN** kind、lifecycle、provenance、evidence、枚举 confidence 和机器 UTC 时间满足 `design.md` schema，数值 confidence 被拒绝

#### AC-001.3 Remember / upsert 契约

- **GIVEN** mutation 显式提供唯一 workflow、shared 或 local scope 和合法 payload
- **WHEN** 无 ID 创建、完全相同 payload 重放、有 ID 更新、未知 ID 更新或 ETag 缺失
- **THEN** 创建生成 UUID；完全相同重放返回 noop；同名不同内容允许新建；更新必须匹配 expected ETag；未知 ID、缺 ETag 或非法 metadata 返回稳定错误且零写入

### REQ-002: 安全发现与 AGENTS 信任边界

作为 Codex Agent，我希望通过固定入口发现 memory，而不是把用户数据提升为指令，以便消除持久化提示注入和索引漂移。

#### AC-002.1 固定区段

- **GIVEN** 标题、正文或 workflow 名包含 Markdown、sentinel 或指令文本
- **WHEN** 执行 index repair 或更新 memory
- **THEN** `AGENTS.md` 只包含版本化固定说明，不包含任何动态用户字符串

#### AC-002.2 实时发现

- **GIVEN** 动态索引缺失或旧索引损坏
- **WHEN** 调用 list 或 recall
- **THEN** 工具从 containment 校验后的 canonical 文件实时扫描并返回当前结果，不依赖 cache

### REQ-003: Shared / Local 物理隐私边界

作为论文作者，我希望团队记忆和本地记忆在文件系统上隔离，以便 local 内容不会因 metadata 错误进入 Git 或默认共享上下文。

#### AC-003.1 Local fail closed

- **GIVEN** `memory.local.md` 已被 Git 跟踪、未被 ignore 或无法证明 Git 状态
- **WHEN** 请求 local mutation
- **THEN** 写入被拒绝并区分非 Git、Git 不可用、已跟踪、未 ignore 或检查失败，返回不泄露 local 正文的可执行诊断，shared 文件保持不变且 mutation 不暗改 `.gitignore`

#### AC-003.2 默认隔离

- **GIVEN** 同一 workflow 同时存在 shared 和 local 记录
- **WHEN** 执行默认 list、recall、AGENTS repair 或提交诊断
- **THEN** local 标题、正文、metadata 和数量均不进入 shared 结果

### REQ-004: 并发安全的记忆生命周期

作为多个并行 Agent，我希望 mutation 使用 workflow 锁与 ETag，以便不同更新不丢失、陈旧更新不静默覆盖。

#### AC-004.1 CAS 冲突

- **GIVEN** 两个调用基于同一条目的旧 ETag
- **WHEN** 第一个更新成功后第二个提交
- **THEN** 第二个返回 conflict 和当前 ETag；若编辑器在工具锁外改写整文件则返回 file-changed conflict，磁盘保留外部或第一个完整结果且无半写

#### AC-004.2 同文件替代

- **GIVEN** 同一 workflow/scope 内多个 active source IDs 和匹配 ETags
- **WHEN** 执行 supersede 或 consolidate apply
- **THEN** 新记录 active、旧记录 superseded 在一次原子 replace 中完成；跨 workflow/scope 请求被拒绝

#### AC-004.3 Forget

- **GIVEN** 一条 active 记录和匹配 ETag
- **WHEN** 执行 forget
- **THEN** 记录转 archived 并保留正文和审计信息；v1 不提供 restore 或 purge

### REQ-005: 有界、确定性、非向量 Recall

作为 orchestrator，我希望用可解释的中英词法检索获得有限上下文，以便在无外部依赖时稳定恢复相关决策和约束。

#### AC-005.1 排序与过滤

- **GIVEN** 多个 workflow、scope、lifecycle 和 kind 的记录
- **WHEN** 对当前 workflow 执行 recall
- **THEN** 先按边界过滤，再按 exact ID/title/phrase、英文 token、CJK bigram 和字段权重排序，零分结果不返回并附 matched_terms

#### AC-005.2 Context budget

- **GIVEN** 候选数量超过 top_k 或序列化结果超过 max_bytes
- **WHEN** 组装 recall 响应
- **THEN** 最多返回 5 条且默认不超过 4096 UTF-8 bytes，只返回完整记录并保持确定性顺序

#### AC-005.3 已知限制

- **GIVEN** 查询与目标记录没有词面重合且没有 alias
- **WHEN** 纯词法 scorer 不能达到最小阈值
- **THEN** 返回空结果或 baseline 诊断，不调用向量、FTS、BM25 或外部服务补偿

### REQ-006: 存储预算与显式 Consolidation

作为 memory 维护者，我希望系统提示容量压力但不自动改写事实，以便上下文有界且科学内容仍由人类或 Agent 审核。

#### AC-006.1 Soft budget

- **GIVEN** active 记录达到 12 条或 16 KiB
- **WHEN** 合法 remember 完成
- **THEN** 写入可成功并返回 needs_consolidation、预算明细和候选 IDs，不自动删除第 13 条

#### AC-006.2 Hard budget

- **GIVEN** 预计写入会使 canonical 文件超过 256 KiB
- **WHEN** mutation 校验预算
- **THEN** 写入失败且原文件不变；响应明确 consolidation/archive 不保证缩小文件，并要求备份或 Git 审查后的人工维护

#### AC-006.3 两阶段合并

- **GIVEN** consolidate plan 的 source IDs、ETags 和 plan ID
- **WHEN** Agent 提供新正文并执行 apply
- **THEN** 工具锁内基于 canonical workflow/scope/source IDs/ETags 重算无状态 plan ID；任一值变化则整体 stale，全部匹配才在单文件中原子完成，程序不生成语义正文或持久化 plan cache

### REQ-007: Progress 独立的工作流上下文

作为 Nature orchestrator，我希望 resume 获得有界 memory context、complete/block 获得 review 提示，同时 progress 仍独立可靠。

#### AC-007.1 Resume

- **GIVEN** progress resume 成功且 memory 可读
- **WHEN** facade 组合结果
- **THEN** 只解析一次 workflow，并返回 progress summary 与有界 recall；`nature_progress.py` 不依赖 memory

#### AC-007.2 Partial failure

- **GIVEN** complete 或 block 已成功落盘，但后置 memory review 失败
- **WHEN** facade 返回 MCP 结果
- **THEN** 整体返回 `ok=true`、`progress_committed=true` 和 `memory_review.status=unavailable` 的结构化 error，不回滚 progress，也不抛出诱导重试 progress mutation 的 JSON-RPC error

#### AC-007.3 Admission review

- **GIVEN** complete/block 产生可能跨会话有用的信息
- **WHEN** facade 生成 memory_review
- **THEN** Agent 显式选择 remember、supersede 或跳过；系统不得自动写入

### REQ-008: 动态事实、证据与稳定引用

作为科研作者，我希望 memory 保留项目决策和证据位置，但不把历史 snapshot 冒充当前权威事实。

#### AC-008.1 动态事实核验

- **GIVEN** journal scope、APC、影响因子、投稿规则、政策或联系方式将进入推荐或交付
- **WHEN** Agent 使用相关 memory
- **THEN** 当次任务访问期刊或出版社官方页面核验 scope、APC、投稿规则、政策和联系方式，影响因子访问其权威发布方；记录 source URL、retrieved_at 和 verified/unverified，无法访问时结构化标记当前未核验，不用 snapshot 补成事实；动态事实写入若 requires_live_verification=false 则校验失败

#### AC-008.2 逻辑 locator

- **GIVEN** 标题、行号或 Markdown slug 发生变化
- **WHEN** show/recall 解析 `memory.md#nm_<uuid>`
- **THEN** 仍返回当前路径、scope、lifecycle、evidence 和替代关系；不声称 locator 必然是浏览器可点击 fragment

### REQ-009: Legacy 兼容、显式迁移与安全修复

作为现有使用者，我希望旧文件、引用、命令和 hook 不会因升级突然失效，以便安全迁移到 schema v1。

#### AC-009.1 混合读取

- **GIVEN** 旧 `## M<int> · 标题`、标题版和 schema v1 混合文件
- **WHEN** 执行只读 parse/list/show
- **THEN** 所有可解析条目可见，旧 M ID 保留 alias，未迁移标题版返回临时 legacy_ref 和 requires_migration，读取不修改源文件或伪造稳定 ID

#### AC-009.2 显式迁移

- **GIVEN** legacy workflow
- **WHEN** 先 dry-run 再 migrate
- **THEN** 工具报告生成 ID、碰撞和 diff；单篇原子、重复执行幂等，失败时原文件 byte-for-byte 不变

#### AC-009.3 旧工具与 sentinel

- **GIVEN** 旧 touch/index/check/list 调用或含多个旧 sentinel 的 AGENTS
- **WHEN** 运行兼容 shim 或 index repair
- **THEN** 旧调用获得结果或 deprecated 诊断；repair 在项目锁和备份下写入固定区段，边界不确定时 fail closed

### REQ-010: 可执行验证与发布门槛

作为维护者，我希望规范具有确定性测试、检索指标和 fresh-session Agent eval，以便“能存”不被误报为“能正确记忆”。

#### AC-010.1 确定性 fixture

- **GIVEN** 至少 5 个 workflow、60 条 active shared、10 条 local、10 条 archived/superseded 和至少 50 个 query
- **WHEN** 运行检索评测
- **THEN** 使用版本化 gold IDs 和 0/1/2 相关性等级按 query macro 计算；Recall@3 分母为该 query 全部 relevant IDs，MRR 使用首个 relevant，nDCG@3 排除 no-hit，no-hit FPR 为返回任意结果的 no-hit query 比例；exact/partial/mixed Recall@3 不低于 0.95、总体 MRR 不低于 0.90、总体 nDCG@3 不低于 0.85、no-hit FPR 不高于 0.10

#### AC-010.2 安全与一致性

- **GIVEN** 注入、路径逃逸、cross-workflow、scope、lifecycle、legacy、迁移和并发对抗用例
- **WHEN** 运行每次 PR 的确定性测试
- **THEN** 隔离、引用解析和安全一致性全部通过，隐私/安全泄漏为 0

#### AC-010.3 Agent eval

- **GIVEN** 至少 20 个 `new -> remember -> fresh resume -> recall -> cite` 场景且每个运行 3 次
- **WHEN** 执行 nightly/release eval
- **THEN** 每次运行使用新进程和干净项目副本，锁定 should-remember、must-not-write、expected locator、模型参数、插件和允许工具；60 次 run micro-aggregate 的 durable write precision 不低于 0.90、write recall 不低于 0.80、引用有效率 100%，任一越权调用或隐私泄漏即阻断，并保存确定性断言与双人语义 rubric 证据

---

## 5. 非功能性需求

| ID | 类别 | 描述 | 来源设计约束 |
|:---|:---|:---|:---|
| NFR-001 | 安全 | memory 始终为低信任数据；AGENTS 无动态用户内容；注入用例零越权、零自动工具执行 | 设计 9.2、9.3 |
| NFR-002 | 隐私 | local 进入 Git、shared 结果或其他 workflow 的次数为 0；无法证明 ignore 时 fail closed | 设计 9.1 |
| NFR-003 | 并发 | stale ETag 明确 conflict；不同更新不丢失；无半写和悬空 lifecycle 关系 | 设计 7.3 |
| NFR-004 | 上下文 | 默认 recall 受 top_k 和 4096 UTF-8 bytes 双硬限制；AGENTS 大小不随记忆增长 | 设计 7.1、9.3 |
| NFR-005 | 存储 | active 12 条/16 KiB 为 soft budget，canonical 256 KiB 为 hard safety limit | 设计 7.2 |
| NFR-006 | 兼容性 | stdlib-first，支持仓库现有 Python 运行时、Windows/类 Unix、UTF-8 中文、NFC/NFD、LF/CRLF | 设计 2.3、10 |
| NFR-007 | 确定性 | 相同源数据、配置和 query 产生相同过滤、排序、预算与 locator 结果 | 设计 7.1 |
| NFR-008 | 性能 | 12k 记录全扫描在参考 Windows 环境不超过 1 秒；该指标作为 release benchmark，不作为跨硬件单元测试 | 设计 13.2 |
| NFR-009 | 可审计性 | shared 变更可由 Git、UTC 机器时间和结构化 lifecycle 追踪；不伪造实时核验 | 设计 5、8.3 |
| NFR-010 | 可观测性 | error/warning 包含 workflow、scope、entry ID、rule、ETag 和修复建议，且不泄露 local 正文或 secret | 设计 11 |
| NFR-011 | 依赖 | 核心功能不要求向量、embedding、FTS、BM25、jieba、tiktoken、数据库或外部服务 | 设计 2.3、12 |
| NFR-012 | 人类可读性 | hidden metadata 不破坏自然 Markdown；标题和正文可直接审阅 | 设计 5.1 |

---

## 6. 设计映射

| 需求 ID | 设计章节 | 说明 |
|:---|:---|:---|
| REQ-001 | 4.3、5、6.1、6.3 | 稳定 ID、schema、remember/upsert、MCP 和自然 Markdown |
| REQ-002 | 4.1、9.2、9.3 | 固定 AGENTS 和实时扫描 |
| REQ-003 | 5.2、9.1 | 物理 shared/local 与 Git fail closed |
| REQ-004 | 5.3、6.1、7.3 | 生命周期、锁、ETag 和原子写 |
| REQ-005 | 7.1 | 非向量 scorer、过滤、排序和 context budget |
| REQ-006 | 7.2 | soft/hard budget 与两阶段 consolidation |
| REQ-007 | 6.2、8 | progress-independent facade 与 partial failure |
| REQ-008 | 5.2、8.3 | evidence、动态事实和逻辑 locator |
| REQ-009 | 9.3、10 | legacy、迁移、旧命令和 sentinel repair |
| REQ-010 | 13 | 确定性、指标和 Agent eval |

---

## 7. 约束、假设与超出范围

### 约束

- 规范批准前不得修改业务代码。
- shared/local、稳定 ID、ETag conflict、固定 AGENTS、动态事实实时核验和无向量依赖不得降级。
- v1 mutation 只操作一个明确 workflow 和 scope。
- index/cache 不得成为 canonical truth。

### 假设

- 初始预算和 scoring 参数会由首轮真实 fixture 校准；修改需同步规范和证据。
- 纯词法方案不解决无词面重合的语义查询；可用 aliases 缓解。
- local 只避免默认 Git/共享暴露，不是本机访问控制或 secret storage；非 Git 或无法证明 ignore 时 v1 local mutation 被拒绝。

### 超出范围

- 向量检索、RAG、FTS/BM25 持久索引和跨项目全局记忆。
- 跨 workflow/scope 原子 promote、双写 supersede 或 consolidation。
- 自动 LLM 合并、自动 TTL 删除、物理 archive 分片和 Git 历史重写。
- 期刊官网镜像、动态事实缓存和完整 secret manager。

---

## 8. 审批记录

| 日期 | 审批人 | 决定 | 备注 |
|:---|:---|:---|:---|
| 2026-07-14 | 用户 | 已批准 | 用户确认“我已审批，请立即执行”，进入实现与结尾验收 |
