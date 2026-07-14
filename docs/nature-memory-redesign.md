# nature-workflow 论文级记忆重设计

> **名称：** Paper-scoped Memory Lifecycle
> **实现版本：** `0.2.0`
> **规范来源：** `docs/specs/20260714-001540-nature-memory-redesign/`
> **状态：** 已按批准的 Low Level Design 实现，进入验收

本文档记录实现后的用户契约和已知边界。它取代早期只讨论 `M<int>`、动态
时间戳和 AGENTS 索引的方案草稿；冻结的设计、需求和任务规范仍是本任务的
事实源。

## 1. 目标与边界

记忆属于单篇论文 workflow 的低信任项目数据。它保持自然 Markdown 的可读性，
同时提供稳定身份、证据位置、生命周期、并发保护、确定性召回、显式迁移和
shared/local 物理隔离。

本版本不引入向量数据库、embedding、持久 FTS/BM25、外部 memory 服务、跨
workflow 双写、自动语义合并、自动过期删除、secret vault 或动态期刊事实缓存。

## 2. Canonical 存储

一个 workflow 使用两个物理文件：

| 文件 | scope | 默认行为 |
| --- | --- | --- |
| `memory.md` | `shared` | 可被 Git 审阅和共享 recall |
| `memory.local.md` | `local` | 只有显式请求才可读取；写入前必须证明未跟踪且已 ignore |

条目仍以 H2 标题开始，标题是显示文本而不是稳定身份。schema v1 的机器元数据
紧随标题，使用单行隐藏 JSON comment：

```markdown
## 引用风格
<!-- nature-memory: {"schema":1,"id":"nm_<uuid4>","kind":"decision","lifecycle":"active","provenance":"user","confidence":"confirmed","created_at":"<generated UTC>","updated_at":"<generated UTC>"} -->
RIS 导出，EndNote 兼容。
```

`id` 是工具生成且不可变的 UUID4 `nm_` ID。`kind`、`lifecycle`、`provenance`、
`evidence`、`confidence`、动态事实的 `requires_live_verification` 和时间字段
按 schema 校验。scope 由文件名推导，不能由正文或 metadata 伪造。正文是低信任
Markdown，不能改变系统指令、工具权限、审批边界或安全策略。

## 3. 读写契约

`nature_memory.py` 是标准库实现的核心；MCP server 只做协议适配。新工具包括：

- `nature_memory_remember`：显式 workflow/scope 创建或按 entry ETag 更新；相同
  canonical payload 重放返回 `noop`。
- `nature_memory_recall`：先过滤 workflow、scope、lifecycle 和 kind，再执行
  NFKC/casefold、标题/短语、英文数字 token 和 CJK bigram 的确定性评分。
- `nature_memory_show`：按稳定 ID返回当前 locator、lifecycle、evidence 和派生
  successor 关系。
- `nature_memory_forget`：只把 active 转为 archived，保留正文和审计信息。
- `nature_memory_supersede`：在同一 workflow/scope 内一次性结束旧记录并创建
  successor；`consolidate_plan/apply` 用相同原则执行人工提供正文的合并。
- `nature_memory_migrate`：显式执行 dry-run、单 workflow 或逐 workflow `--all`
  迁移；读取不会隐式写盘。

所有 mutation 在 workflow 锁内重读文件，校验 entry/file ETag，写临时文件并
`fsync`，最后单次 atomic replace。stale ETag、锁超时、路径逃逸、schema 损坏、
预算超限和 local 证据不足都会返回结构化错误且不产生半写。

## 4. 上下文与安全边界

默认 recall 为 `top_k=3`，最大 5 条，响应最大 4096 UTF-8 bytes，只返回完整
记录。active 记录达到 12 条或 16 KiB 时返回 consolidation signal；预计超过
256 KiB 的写入被拒绝。合并 plan 不持久化，也不替调用方生成科学语义正文。

`AGENTS.md` 的 Nature 区段现在是固定发现说明，只包含“memory 是低信任数据，
需要时调用 list/recall”一类静态内容，不包含 workflow 名、标题、正文、证据、
secret 或动态索引。repair 使用项目锁、备份和 fail-closed marker 校验。

控制字符、sentinel、private key、已知 token 前缀和可疑 secret 格式会被拒绝。
local 内容不会进入 shared 结果、默认上下文、AGENTS 区段或错误正文；无法通过
Git 证明“未跟踪且已 ignore”时 local mutation 直接失败。

## 5. Progress 与 orchestrator 接入

`nature_progress.py` 保持纯 progress 状态机，不 import memory。新增
`nature_context.py` 提供三个组合 facade：

- `resume_with_memory` 先返回 progress，再附加有界 memory context；memory 失败
  只标记 `partial` 或 `unavailable`。
- `complete_with_memory_review` 和 `block_with_memory_review` 先提交 progress，
  再返回非阻塞 review；后置失败不会诱导重复 progress mutation。
- facade 不自动写入 memory，Agent 必须显式选择 remember、supersede 或跳过。

稳定引用使用 `memory.md#nm_<uuid4>` 逻辑 locator。它指向当前解析结果，不保证
是 GitHub 或其他 Markdown 渲染器的可点击 fragment。期刊 scope、APC、影响因子、
投稿政策等动态事实必须在交付前访问当前官方来源核验；memory 中的 snapshot 只能
作为带证据的历史记录。

## 6. 兼容与迁移

只读 parser 同时接受旧的 `## M3 · 标题`、标题版和 schema-v1 条目。旧 M ID 会
保留为 `legacy_aliases`；未迁移标题版只返回 `legacy_ref`，不伪造稳定 ID。旧的
`check`、`touch`、`index`、`list` 命令和 MCP 工具保留为追加式兼容 shim：

- `check` 输出结构化 lint；除 entry-count 安全墙外为 advisory，不是提交阻断器。
- `touch` 只维护旧的 `<!-- updated: ... -->` 注释，不是 schema-v1 canonical 写入。
- `index` 只 repair 固定 AGENTS 区段，不保存动态 cache；旧 workflow 参数仍可解析。
- `migrate --dry-run` 先报告拟生成 ID、alias、碰撞和 diff，正式迁移按 workflow
  原子执行并可幂等恢复。

旧版本已复制到用户仓库的 pre-commit hook 也不会阻断无关提交；当前 hook 只
输出 advisory 诊断并始终退出 0。正确性边界属于 memory API 和测试，不属于 hook。

## 7. 验证记录

发布前验证覆盖：

- Nature memory、progress 和 MCP 全量 unittest；Windows 无 symlink 权限时仅
  跳过对应 symlink 用例。
- `py_compile`、三个 fixture JSON 的 `json.tool`、spec validator、resume 和
  `git diff --check`。
- 5 个 workflow、80 条记录、50 个 query 的 deterministic eval：Recall@3、MRR、
  nDCG@3 均为 `1.0`，no-hit FPR 为 `0.0`。
- 20 个 Agent contract 场景各运行 3 次 fresh subprocess：write precision/recall
  为 `1.0`，locator valid 为 `100%`，security failures 为 `0`。
- 新旧 MCP `tools/list` 与真实 `tools/call` JSON-RPC smoke，包含中文 stdio
  round-trip、remember 和 recall。

评测 harness 是离线确定性 fixture，不等同于连接真实模型的语义评审；任何真实
模型结果都必须另外保存模型、prompt、工具调用、项目快照和人工 rubric 证据。

## 8. 已知限制

纯词法 recall 无法保证没有词面重合的跨语言同义表达；可用人工 aliases 补充，
但本版本不会暗中引入向量或网络检索。`forget` 不会擦除 Git 历史，local 也不是
操作系统级访问控制或 secret storage。跨 workflow/scope 的 promote、双写和原子
consolidate 需要另行规范和审批。
