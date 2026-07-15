# nature-workflow 论文级记忆重设计任务清单

> **功能名称：** Paper-scoped Memory Lifecycle
> **关联规范：** `docs/specs/20260714-001540-nature-memory-redesign/design.md` · `docs/specs/20260714-001540-nature-memory-redesign/requirements.md`
> **状态：** Accepted
> **当前任务：** n/a
> **进度：** 12 / 12 已完成
> **最后更新：** 2026-07-15 06:05:06

---

## 执行规则

1. `design.md` 是主事实源，`requirements.md` 的需求与门槛必须由设计支撑。
2. 人类回复 `批准规范，启动执行` 后，先通过 Spec Progress approve 冻结基线；未批准时禁止修改业务实现。
3. 每项任务开始、完成、阻塞或跳过都必须通过 `spec_progress.py` 或 MCP 工具更新，并记录验证证据。
4. 批准后若数据模型、外部 API、隐私默认、任务图或验收门槛需要变化，立即停止实现，运行 sync-check 标记 reapproval-required，再更新规范并重新审批。
5. 当前 dirty worktree 是迁移输入；实现必须保留用户已有改动意图，不得重置或覆盖未提交业务文件。
6. 向量数据库、embedding、持久 FTS/BM25 和外部 memory 服务不属于本任务图。

---

## 阶段 1：Canonical 数据与事务边界

- [x] **T-001:** 建立 canonical schema、稳定身份与混合格式只读解析
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (40 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 06:54:25
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: 无
  - 风险: high
  - 覆盖: REQ-001, REQ-008, REQ-009, NFR-006, NFR-007, NFR-009, NFR-010, NFR-012
  - 可并行: 否
  - 验证标准: 保留当前 dirty 草稿的有效意图；hidden JSON metadata、UUID4 stable ID 和自然 Markdown 可往返；legacy M alias、未迁移标题版和 schema v1 可混合只读；read 不写盘，标题版返回 legacy_ref 而不伪造稳定 ID；重复 ID、未知 schema 和非法 comment 边界返回稳定诊断。

- [x] **T-002:** 实现 shared/local 路径、隐私与低信任输入边界
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (44 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:01:05
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-001
  - 风险: high
  - 覆盖: REQ-002, REQ-003, REQ-008, NFR-001, NFR-002, NFR-006, NFR-010, NFR-011
  - 可并行: 否
  - 验证标准: 路径 containment 与 symlink escape 被拒绝；local 只有在 Git 证明未跟踪且已 ignore 时可 mutation，非 Git、Git 失败、已跟踪或未 ignore 均零写入且不暗改 `.gitignore`；默认 shared 结果不泄露 local；固定 secret 格式、控制字符和 sentinel 注入按版本化规则处理。

- [x] **T-003:** 实现 workflow 锁、双层 ETag 与 remember/upsert 原子事务
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (49 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:08:53
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-002
  - 风险: high
  - 覆盖: REQ-001, REQ-004, NFR-003, NFR-006, NFR-009, NFR-010
  - 可并行: 否
  - 验证标准: Windows 与类 Unix 使用同一 workflow lock 外部契约；锁内重读并执行 raw-entry ETag CAS，replace 前重验 file snapshot ETag；临时文件 flush/fsync 后单次 replace；不同 workflow 可并发；改标题 ID 不变；完全相同 create 重放为 noop，未知 ID、缺 ETag、锁超时和外部文件改写均可观测且无半写。

- [x] **T-004:** 实现 active 生命周期、forget、supersede 与稳定 locator
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (52 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:12:52
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-003
  - 风险: high
  - 覆盖: REQ-004, REQ-008, NFR-003, NFR-009, NFR-010, NFR-012
  - 可并行: 否
  - 验证标准: 只有 active 可更新、归档、替代或参与合并；forget 只转 archived，supersede 在同 workflow/scope 单次 replace 中创建 successor 并终结 source；v1 无 restore/purge；跨 workflow/scope 双写被拒绝；show 可按稳定逻辑 locator 返回当前位置和派生替代关系。

- [x] **T-005:** 实现存储预算与无状态 consolidate plan/apply
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (56 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:20:43
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-004
  - 风险: high
  - 覆盖: REQ-006, NFR-003, NFR-005, NFR-007, NFR-009, NFR-010
  - 可并行: 否
  - 验证标准: active 达到 12 条或 16 KiB 时写入成功并返回 consolidation signal，预计超过 256 KiB 时原文件不变；plan ID 由 canonical workflow/scope/source IDs/ETags 确定且不持久化；apply 锁内重算并全量 CAS，stale plan 整体拒绝，正文必须由调用方提供且单次 replace 后 active 数量下降。

---

## 阶段 2：发现、召回、迁移与工作流接入

- [x] **T-006:** 固定 AGENTS 信任区并保留旧命令 repair shim
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (58 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:30:49
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`, `plugins/nature-workflow/assets/hooks/pre-commit-nature-memory`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-002
  - 风险: high
  - 覆盖: REQ-002, REQ-009, NFR-001, NFR-004, NFR-006, NFR-010, NFR-011
  - 可并行: 否
  - 验证标准: AGENTS 固定块不含 workflow、标题、正文或其他动态字符串且大小不随 memory 增长；不存在动态 cache；repair 使用项目锁与备份，只处理零个或唯一合法 marker pair，多个、不完整、逆序或嵌套 marker 均 fail closed；check/touch/index/list 追加式兼容且旧 hook 不阻断工作流。

- [x] **T-007:** 实现实时 list/show/recall 与有界确定性评分
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (58 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python plugins/nature-workflow/scripts/test_nature_memory_recall.py (5 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py plugins/nature-workflow/scripts/test_nature_memory_recall.py; git diff --check
  - 完成时间: 2026-07-14 07:39:08
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory_recall.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory_recall.py`
  - 依赖: T-004
  - 风险: medium
  - 覆盖: REQ-002, REQ-005, REQ-008, NFR-004, NFR-007, NFR-008, NFR-010, NFR-011, NFR-012
  - 可并行: 否
  - 验证标准: scope、lifecycle、kind 先过滤；NFKC/casefold 后 exact ID/title/phrase 优先于英文数字 token 与 CJK bigram；零分返回空，tie-break 稳定并返回 matched_terms；默认 top_k=3、最大 5、响应不超过 4096 UTF-8 bytes 且不截断记录；默认仅当前 workflow/shared，跨篇或 local 必须显式请求，无外部检索依赖。

- [x] **T-008:** 实现显式 legacy migration 与逐 workflow 恢复
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_memory.py (61 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check
  - 完成时间: 2026-07-14 07:48:38
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_memory.py`, `plugins/nature-workflow/scripts/test_nature_memory.py`
  - 验证命令: `python plugins/nature-workflow/scripts/test_nature_memory.py`
  - 依赖: T-005, T-006, T-007
  - 风险: high
  - 覆盖: REQ-001, REQ-004, REQ-009, NFR-003, NFR-006, NFR-007, NFR-009, NFR-010, NFR-012
  - 可并行: 否
  - 验证标准: dry-run 报告拟生成 ID、legacy alias、碰撞和预计 diff；单 workflow 在锁内原子迁移，失败 byte-for-byte 不变；all 模式逐篇幂等、可恢复且不冒充全局事务；旧 timestamp 保留可证明历史，重复标题不合并，歧义引用硬失败。

- [x] **T-009:** 接入 progress-independent nature_context facade 与 MCP 契约
  - 状态: done
  - 验证证据: python plugins/nature-workflow/scripts/test_nature_progress.py (22 tests OK); python plugins/nature-workflow/scripts/test_nature_progress_server.py (3 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_context.py plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/mcp/nature_progress_server.py; git diff --check
  - 完成时间: 2026-07-14 08:13:31
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/nature_context.py`, `plugins/nature-workflow/scripts/nature_progress.py`, `plugins/nature-workflow/mcp/nature_progress_server.py`, `plugins/nature-workflow/scripts/test_nature_progress.py`, `plugins/nature-workflow/scripts/test_nature_progress_server.py`
  - 验证命令: 依次运行 `python plugins/nature-workflow/scripts/test_nature_progress.py` 和 `python plugins/nature-workflow/scripts/test_nature_progress_server.py`
  - 依赖: T-008
  - 风险: high
  - 覆盖: REQ-007, REQ-008, REQ-009, NFR-001, NFR-004, NFR-006, NFR-009, NFR-010, NFR-011
  - 可并行: 否
  - 验证标准: canonical workflow 只解析一次，nature_progress 不 import memory；resume 返回有界 context，单 scope 失败为 partial；complete/block 先提交 progress 并返回 progress_committed，后置失败只进入 memory_review unavailable 而不抛 JSON-RPC error；新旧 tools/list 和真实 tools/call 均符合追加式 schema，响应丢失后的调用方先 resume/status 核验。

---

## 阶段 3：对抗验证、Agent Eval 与发布收尾

- [x] **T-010:** 补齐安全、隐私、迁移与并发对抗回归
  - 状态: done
  - 验证证据: python -B -m unittest discover -s plugins/nature-workflow/scripts -p "test_nature_memory*.py" (74 tests OK, 2 symlink tests skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py plugins/nature-workflow/scripts/test_nature_memory_recall.py plugins/nature-workflow/scripts/test_nature_memory_safety.py plugins/nature-workflow/scripts/test_nature_memory_concurrency.py; git diff --check
  - 完成时间: 2026-07-14 08:26:41
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/scripts/test_nature_memory_safety.py`, `plugins/nature-workflow/scripts/test_nature_memory_concurrency.py`
  - 验证命令: `python -B -m unittest discover -s plugins/nature-workflow/scripts -p "test_nature_memory*.py"`
  - 依赖: T-009
  - 风险: medium
  - 覆盖: REQ-003, REQ-004, REQ-009, REQ-010, NFR-001, NFR-002, NFR-003, NFR-006, NFR-007, NFR-010
  - 可并行: 是
  - 验证标准: 注入、路径逃逸、scope/local、secret hard reject、legacy/migrate、损坏 sentinel、CRLF、NFC/NFD、锁超时、stale entry/file ETag、不同 entry 并发和无半写均有确定性回归；local 正文不进入 shared 结果、日志或错误，安全/隐私失败为零。

- [x] **T-011:** 建立 recall 指标、性能基准与 fresh-session Agent eval
  - 状态: done
  - 验证证据: python plugins/nature-workflow/evals/nature_memory_eval.py --mode deterministic (5 workflows, 80 records, 50 queries; Recall@3=1.0, MRR=1.0, nDCG@3=1.0, no-hit FPR=0.0); python plugins/nature-workflow/evals/nature_memory_eval.py --mode agent --runs 3 (20 scenarios x 3 fresh processes; write precision=1.0, write recall=1.0, locator valid=100%, security failures=0); python -m json.tool plugins/nature-workflow/evals/fixtures/recall_cases.json; python -m json.tool plugins/nature-workflow/evals/fixtures/agent_scenarios.json; python -m py_compile plugins/nature-workflow/evals/nature_memory_eval.py
  - 完成时间: 2026-07-14 09:05:46
  - 备注: n/a
  - 涉及文件: `plugins/nature-workflow/evals/nature_memory_eval.py`, `plugins/nature-workflow/evals/fixtures/recall_cases.json`, `plugins/nature-workflow/evals/fixtures/agent_scenarios.json`, `plugins/nature-workflow/evals/README.md`
  - 验证命令: 依次运行 `python plugins/nature-workflow/evals/nature_memory_eval.py --mode deterministic` 和 `python plugins/nature-workflow/evals/nature_memory_eval.py --mode agent --runs 3`
  - 依赖: T-009
  - 风险: medium
  - 覆盖: REQ-005, REQ-007, REQ-008, REQ-010, NFR-001, NFR-002, NFR-004, NFR-007, NFR-008, NFR-009, NFR-010, NFR-011
  - 可并行: 是
  - 验证标准: 版本化 fixture 固定至少 5 个 workflow、80 条记录、50 个 query、gold IDs 和相关性等级；按规范口径达到 Recall@3、MRR、nDCG@3 与 no-hit FPR 门槛；记录单 workflow 与 12k all-workflows benchmark；20 场景各 3 次使用新进程/干净副本，write precision、write recall、locator 和零泄漏门槛全部满足并保存模型、工具调用、确定性断言和双人 rubric 证据。

- [x] **T-012:** 同步文档、hook、manifest 并执行发布前全量验证
  - 验证命令: 依次运行 Nature 全量 unittest、py_compile、新旧 MCP JSON-RPC smoke、deterministic 与 offline fixture Agent eval（connected model evaluation=false）、三个 JSON 文件的 `python -m json.tool`、`python plugins/spec-workflow/scripts/validate_spec.py docs/specs/20260714-001540-nature-memory-redesign --workflow design-first`、`python plugins/spec-workflow/scripts/validate_spec.py docs/specs/20260714-001540-nature-memory-redesign --resume` 和 `git diff --check`
  - 验证标准: README、skill、orchestrator、hook、CLI/MCP schema、动态事实、隐私与已知限制完全一致；plugin/MCP/marketplace 版本和路径一致；所有测试、eval、JSON、编译、MCP smoke、spec validator、resume 与 whitespace 检查退出 0；只记录本任务声明路径的实现和发布证据，再进入 pre-acceptance/final acceptance。
  - 状态: done
  - 验证证据: 99 Nature unittest passed (2 Windows symlink skips); compileall passed; deterministic eval 5 workflows/80 records/50 queries Recall@3=1.0 MRR=1.0 nDCG@3=1.0 no-hit FPR=0.0; agent eval 20 scenarios x 3 fresh processes write precision=1.0 write recall=1.0 locator=100% security failures=0; MCP JSON-RPC smoke passed; fixture and manifest JSON validation passed; spec validator/resume and git diff --check run
  - 完成时间: 2026-07-14 09:36:21
  - 备注: 同步 README、docs/nature-memory-redesign.md、Nature skill、orchestrator、hook、MCP version/config、plugin manifest 和 marketplace 到 schema-v1 / 0.2.0；离线 fixture eval 不声明 connected model evaluation。
  - 涉及文件: `README.md`, `docs/nature-memory-redesign.md`, `plugins/nature-workflow/skills/nature-workflow/SKILL.md`, `plugins/nature-workflow/skills/nature-orchestrator/static/core/workflow.md`, `plugins/nature-workflow/assets/hooks/pre-commit-nature-memory`, `plugins/nature-workflow/.mcp.json`, `plugins/nature-workflow/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`
  - 依赖: T-010, T-011
  - 风险: medium
  - 覆盖: REQ-008, REQ-009, REQ-010, NFR-006, NFR-009, NFR-010, NFR-012
  - 可并行: 否

---

## 执行 Waves

| Wave | 任务 | 说明 |
|:---|:---|:---|
| 1 | T-001 | 先冻结 canonical schema 与兼容解析边界 |
| 2 | T-002 | 在 schema 上建立物理 scope 与低信任边界 |
| 3 | T-003 | 写路径必须先闭合锁、CAS 与原子替换 |
| 4 | T-004 | 生命周期依赖稳定事务原语 |
| 5 | T-005 | 预算与合并依赖生命周期 |
| 6 | T-006 | 固定 AGENTS 与 compatibility repair |
| 7 | T-007 | 实时发现与词法召回 |
| 8 | T-008 | 在完整读写合同上执行显式迁移 |
| 9 | T-009 | 最后接入 facade 与 MCP |
| 10 | T-010, T-011 | 代码路径稳定后并行执行对抗回归与 eval |
| 11 | T-012 | 汇总文档、版本和发布前证据 |

---

## 风险标记

| 任务 ID | 风险类别 | 风险描述 | 审查要求 |
|:---|:---|:---|:---|
| T-001 | 数据模型 / 兼容 | stable ID 与混合 parser 错误会使旧引用失效 | 人类深度审查 schema 与 fixture |
| T-002 | 隐私 / 安全 | local 或路径判断错误会造成数据泄漏 | fail-closed 对抗审查 |
| T-003 | 并发 / 一致性 | 锁或 ETag 缺口会导致 lost update | 并发与外部编辑双重测试 |
| T-004 | 生命周期 | 错误状态转换会破坏审计链 | 单文件事务和终态审查 |
| T-005 | 数据维护 | stale plan 或预算误判会覆盖事实 | 全量 CAS 与原文件不变证明 |
| T-006 | Prompt injection | sentinel repair 可能吞掉 AGENTS 正文 | 多 marker 默认拒绝 |
| T-007 | 检索 / 上下文 | 假阳性或预算截断会污染 Agent context | gold fixture 与字节级断言 |
| T-008 | 迁移 / 回滚 | legacy 批量迁移可能不可逆 | dry-run、备份与逐篇恢复 |
| T-009 | 工作流一致性 | partial failure 可能诱导重复 progress mutation | JSON-RPC 真实调用审查 |
| T-010 | 测试完备性 | 未覆盖的对抗路径会形成虚假安全感 | 独立安全与并发测试 |
| T-011 | 评测可信度 | 指标口径或 judge 偏差会制造虚假通过 | 版本化 gold 与双人 rubric |
| T-012 | 发布一致性 | 文档、manifest 与实现漂移 | 全量命令和路径清单复核 |

---

## 完成日志

| 任务 ID | 完成时间 | Commit Hash | 验证证据 | 备注 |
|:---|:---|:---|:---|:---|
| T-001 | 2026-07-14 06:54:25 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (40 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-002 | 2026-07-14 07:01:05 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (44 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-003 | 2026-07-14 07:08:53 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (49 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-004 | 2026-07-14 07:12:52 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (52 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-005 | 2026-07-14 07:20:43 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (56 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-006 | 2026-07-14 07:30:49 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (58 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-007 | 2026-07-14 07:39:08 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (58 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python plugins/nature-workflow/scripts/test_nature_memory_recall.py (5 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py plugins/nature-workflow/scripts/test_nature_memory_recall.py; git diff --check | n/a |
| T-008 | 2026-07-14 07:48:38 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_memory.py (61 tests OK, 1 symlink test skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py; git diff --check | n/a |
| T-009 | 2026-07-14 08:13:31 | d6ec024 | python plugins/nature-workflow/scripts/test_nature_progress.py (22 tests OK); python plugins/nature-workflow/scripts/test_nature_progress_server.py (3 tests OK); python -m py_compile plugins/nature-workflow/scripts/nature_context.py plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/mcp/nature_progress_server.py; git diff --check | n/a |
| T-010 | 2026-07-14 08:26:41 | d6ec024 | python -B -m unittest discover -s plugins/nature-workflow/scripts -p "test_nature_memory*.py" (74 tests OK, 2 symlink tests skipped because Windows symlink privilege is unavailable); python -m py_compile plugins/nature-workflow/scripts/nature_memory.py plugins/nature-workflow/scripts/test_nature_memory.py plugins/nature-workflow/scripts/test_nature_memory_recall.py plugins/nature-workflow/scripts/test_nature_memory_safety.py plugins/nature-workflow/scripts/test_nature_memory_concurrency.py; git diff --check | n/a |
| T-011 | 2026-07-14 09:05:46 | d6ec024 | python plugins/nature-workflow/evals/nature_memory_eval.py --mode deterministic (5 workflows, 80 records, 50 queries; Recall@3=1.0, MRR=1.0, nDCG@3=1.0, no-hit FPR=0.0); python plugins/nature-workflow/evals/nature_memory_eval.py --mode agent --runs 3 (20 scenarios x 3 fresh processes; write precision=1.0, write recall=1.0, locator valid=100%, security failures=0); python -m json.tool plugins/nature-workflow/evals/fixtures/recall_cases.json; python -m json.tool plugins/nature-workflow/evals/fixtures/agent_scenarios.json; python -m py_compile plugins/nature-workflow/evals/nature_memory_eval.py | n/a |
| T-012 | 2026-07-14 09:36:21 | d6ec024 | 99 Nature unittest passed (2 Windows symlink skips); compileall passed; deterministic eval 5 workflows/80 records/50 queries Recall@3=1.0 MRR=1.0 nDCG@3=1.0 no-hit FPR=0.0; agent eval 20 scenarios x 3 fresh processes write precision=1.0 write recall=1.0 locator=100% security failures=0; MCP JSON-RPC smoke passed; fixture and manifest JSON validation passed; spec validator/resume and git diff --check run | 同步 README、docs/nature-memory-redesign.md、Nature skill、orchestrator、hook、MCP version/config、plugin manifest 和 marketplace 到 schema-v1 / 0.2.0；离线 fixture eval 不声明 connected model evaluation。 |
| T-011 | 2026-07-15 00:00:00 | 6bb7d9a | deterministic eval and agent eval --runs 3 passed; Recall@3/MRR/nDCG@3=1.0; no-hit FPR=0.0; 20 scenarios x 3 fresh processes; write precision/recall=1.0; locator=true; security failures=0; external reviewer_verdicts.json disagreements=0; connected_model_evaluation=false | round 5 acceptance checkpoint |
| T-012 | 2026-07-15 00:00:01 | 6bb7d9a | 171 Nature script tests passed (9 skips); WSL safety/concurrency 19 passed; MCP JSON-RPC 10 passed; compile, JSON fixtures, spec validation, resume, and git diff --check passed | current round 5 checkpoint; eval is offline and does not claim connected model evaluation |
