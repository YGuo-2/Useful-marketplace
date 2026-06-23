# Requirements-First 完整使用示例

本文档展示一个从 intake 到最终 acceptance 的端到端 Spec workflow 工作流。

---

## 场景：为博客应用添加评论功能

### Intake 与路由

**用户输入：**

> 我需要给博客应用添加评论功能，登录用户可以在文章下面发表评论。

**智能体响应：**

我读到了Spec workflow技能。
我会先按照“spec-intake”完成需求澄清。

已运行 `spec_progress.py discover docs/specs/`。未发现未完成 workflow，已创建新的 `<specs_dir>`：`docs/specs/20260615-103000-comments`。

已检查现有应用说明与路由结构，当前请求是新增用户能力，不是修复既有错误行为，也没有固定技术设计起点。

## Spec 路由决定

- 路径：Feature / Requirements-First
- Design-First 粒度：n/a
- Intake 状态：需要反问
- 原因：用户提出新增评论能力，未给出固定技术设计起点
- 下一步：需求澄清

我会按照“Feature / Requirements-First”分支来完成。

## 需求澄清

Round 1 | Target: scope

1. 评论是否只支持平级评论，还是需要嵌套回复？

**用户回复：**

> 只做平级评论。

## 需求澄清

Round 2 | Target: decision-boundaries

1. 发表评论和删除评论分别需要哪些权限？哪些能力明确不进入本期？

**用户回复：**

> 必须登录才能发，作者可以删自己的评论，管理员可以删任何评论；审核、敏感词和反垃圾先不做。

## Intake Handoff / 澄清交接摘要

- Status: complete
- Route recommendation: Requirements-First
- Confirmed facts: 新增平级评论；登录用户可发；作者和管理员可删
- Scope: 评论数据、创建/删除服务、评论 API、权限测试
- Non-goals: 嵌套回复、审核、敏感词、反垃圾
- Decision boundaries: 权限规则按用户回复固定；实现细节可沿用现有栈
- Success criteria: 登录发布、未登录拦截、作者/管理员删除权限通过验证
- Assumptions: n/a
- Risks: 权限和数据模型迁移需在 architecture/tasks 中覆盖
- Next step: 返回 `spec-workflow` 路由。

---

### 规范工件生成

智能体生成：

- `<specs_dir>/product.md`
- `<specs_dir>/architecture.md`
- `<specs_dir>/tasks.md`
- `<specs_dir>/progress.md`
- `<specs_dir>/spec.yml`

#### `<specs_dir>/product.md` 节选

```markdown
### US-001: 发表评论

**作为**已登录用户，**我希望**能在文章下方发表评论，**以便**分享我的观点。

#### 验收标准

- **GIVEN** 用户已登录且正在查看一篇文章
- **WHEN** 用户输入 1-500 字评论并点击发布
- **THEN** 评论显示在文章评论列表中，包含作者名和发布时间
```

#### `<specs_dir>/tasks.md` 节选

```markdown
- [ ] **T-001:** 创建 comments 数据模型和迁移
  - 状态: pending
  - 验证命令: pytest tests/test_comments_migration.py
  - 验证证据: pending
  - 依赖: 无
  - 风险: medium
  - 覆盖: US-001, AC-001.1
  - 可并行: 否
  - 验证标准：迁移可执行，comments 表包含文章、作者、内容和时间字段

- [ ] **T-002:** 实现评论创建与删除服务
  - 状态: pending
  - 验证命令: pytest tests/test_comments_service.py
  - 验证证据: pending
  - 依赖: T-001
  - 风险: medium
  - 覆盖: US-001, AC-001.2
  - 可并行: 否
  - 验证标准：作者和管理员权限测试通过

- [ ] **T-003:** 接入评论 API 并补充验收测试
  - 验证标准：登录发布、未登录拦截、删除权限测试通过
```

**智能体输出：**

> 规范工件已生成。请审查 `<specs_dir>` 下的工件。
> 结构校验可运行：
>
> ```bash
> python plugins/spec-workflow/scripts/validate_spec.py <specs_dir> --workflow requirements-first
> python plugins/spec-workflow/scripts/spec_progress.py init <specs_dir>
> python plugins/spec-workflow/scripts/validate_spec.py <specs_dir> --resume
> ```
>
> 通过校验仍不代表批准实施。确认无误后，请回复 `批准规范，启动执行`；收到批准后我会运行 `spec_progress.py approve` 冻结规范基线。

**用户回复：**

> 批准规范，启动执行

---

### 受控实施

**智能体：**

> 已收到批准，先冻结已批准规范和任务计划基线。

```bash
python plugins/spec-workflow/scripts/spec_progress.py approve <specs_dir> --evidence "批准规范，启动执行"
```

> 锁定第一个未完成任务：T-001 创建 comments 数据模型和迁移。

智能体先记录断点，再只实现 T-001：

```bash
python plugins/spec-workflow/scripts/spec_progress.py start <specs_dir> T-001
```

运行该任务的验证后，通过受控工具更新 `tasks.md`、`progress.md` 和 `spec.yml`：

```bash
python plugins/spec-workflow/scripts/spec_progress.py complete <specs_dir> T-001 --evidence "pytest tests/test_comments_migration.py passed"
```

```markdown
- [x] **T-001:** 创建 comments 数据模型和迁移
```

如果 T-002、T-003 仍未完成，智能体只在当前任务完成后询问是否继续。

---

### 最终验收

当 `<specs_dir>/tasks.md` 没有未完成的 `- [ ]` 任务后，智能体进入 `spec-acceptance`。

**智能体：**

> 本地 pre-acceptance 已通过，但这不等同于最终验收。

> 结尾验收需要按 `tasks.md` 编排子 agent 进行审查和对抗审查。请明确授权我启动子 agent 后，我再继续验收流程。

**用户回复：**

> 授权启动子 agent 进行最终验收。

**智能体输出节选：**

```markdown
## Spec workflow 完成结果

- 流程：Requirements-First
- 规范：product.md、architecture.md、tasks.md
- Tasks：全部完成
- 验证：迁移测试、权限测试、API 验收测试已通过
- 结尾验收：通过
- 最终结论：整个 Spec workflow 流程已完成。
```

---

## 关键要点

1. Intake 先检查上下文，再通过多轮高价值问题关闭目标、范围、非目标、决策边界和验收标准。
2. 选定的 `<specs_dir>` 是实施依据，validator 只是结构检查。
3. 首选审批短语是 `批准规范，启动执行`；批准后必须运行 `spec_progress.py approve` 或 MCP `spec_approve` 冻结基线。
4. 每次只实施一个可执行 task，并用 `spec_progress.py` 或 MCP 工具更新状态。
5. `progress.md` 用于断线恢复，`spec.yml` 用于 Kiro 兼容索引和冻结基线。
6. 最终完成必须经过严格的多 agent acceptance；pre-acceptance 只是本地预检。
