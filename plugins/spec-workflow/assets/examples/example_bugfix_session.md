# Bugfix Spec 完整使用示例

本文档展示如何用 Bugfix 分支处理“先证据、再根因、后最小修复”的缺陷修复。

---

## 场景：订单接口重复提交导致库存双扣

### Intake 与路由

**用户输入：**

> 线上有个 bug，订单接口偶尔会重复扣减库存。帮我修一下。

**智能体响应：**

我读到了Spec workflow技能。
我会先按照“spec-intake”完成需求澄清。

已运行 `spec_progress.py discover docs/specs/`。未发现未完成 workflow，已创建新的 `<specs_dir>`：`docs/specs/20260615-103000-inventory-dedup`。

已检查 issue 描述和近期变更记录。当前目标是恢复既有预期行为，而不是新增产品能力。

## Spec 路由决定

- 路径：Bugfix
- Design-First 粒度：n/a
- Intake 状态：需要反问
- 原因：目标是修复既有错误行为，并且涉及库存一致性与线上回归风险
- 下一步：Bug 分析澄清

我会按照“Bugfix”分支来完成。

> [!WARNING]
> 高风险变更警告：当前任务涉及生产库存一致性与线上回归风险，必须进行人类深度审查，切勿草率合并。

## Bug 分析澄清

Round 1 | Target: bug-evidence

1. 重复扣库存时，是否也重复创建订单，还是只有库存被重复扣减？

**用户回复：**

> 订单只创建一次，但库存有时扣两次；有两条 Trace，最近把下单链路改成异步重试。

## Bug 分析澄清

Round 2 | Target: unchanged-behavior

1. 哪些行为必须保持不变，例如接口契约、性能目标、幂等键策略或回滚要求？

**用户回复：**

> 不能改变现有接口契约，也不能影响正常下单性能；不新增外部幂等键参数，回滚时移除内部保护即可。

## Intake Handoff / 澄清交接摘要

- Status: complete
- Route recommendation: Bugfix
- Confirmed facts: 订单只创建一次；库存偶发双扣；有两条 Trace；近期引入异步重试
- Scope: 库存扣减重复消费路径、复现证明、最小幂等保护、回归测试
- Non-goals: 改接口契约、新增外部幂等键参数、无关下单重构
- Decision boundaries: 根因需由证据证明；修复必须保持现有接口和正常性能
- Success criteria: 未修复前复现失败，修复后库存只扣一次，不变行为测试通过
- Assumptions: n/a
- Risks: 生产库存一致性和回滚路径需在 design/tasks 中覆盖
- Next step: 返回 `spec-workflow` 路由。

---

### 规范工件生成

智能体生成：

- `<specs_dir>/bugfix.md`
- `<specs_dir>/design.md`
- `<specs_dir>/tasks.md`
- `<specs_dir>/progress.md`
- `<specs_dir>/spec.yml`

#### `<specs_dir>/bugfix.md` 节选

```markdown
## 当前错误行为

### BUG-001: 重试请求导致库存重复扣减

- **WHEN** 同一订单消息在异步重试窗口内被重复消费
- **THEN** 系统当前会再次调用库存扣减逻辑，导致库存被重复扣减

## 必须保持不变的行为

### SAFE-001: 正常下单链路保持原有响应契约

- **WHEN** 用户提交一次合法下单请求
- **THEN** 系统仍应保持现有响应结构、状态码和性能目标不变
```

#### `<specs_dir>/design.md` 节选

```markdown
## 根因分析

根因：异步重试后的消息消费路径缺少以订单号为粒度的幂等保护。

## 修复策略

在库存扣减入口增加订单粒度幂等检查，只保护重复消费路径，不改变正常下单接口契约。
```

#### `<specs_dir>/tasks.md` 节选

```markdown
- [ ] **B-001:** 建立重复消费导致双扣库存的失败证明
  - 状态: pending
  - 验证命令: pytest tests/test_inventory_retry.py
  - 验证证据: pending
  - 依赖: 无
  - 风险: high
  - 覆盖: BUG-001
  - 可并行: 否
  - 验证标准：未修复前集成测试稳定失败，并证明库存扣减执行两次

- [ ] **B-002:** 为库存扣减路径添加订单粒度幂等保护
  - 状态: pending
  - 验证命令: pytest tests/test_inventory_retry.py
  - 验证证据: pending
  - 依赖: B-001
  - 风险: high
  - 覆盖: FIX-001
  - 可并行: 否
  - 验证标准：B-001 转为通过，且不改变现有下单接口契约

- [ ] **B-003:** 补充正常单次下单与相邻路径回归测试
  - 状态: pending
  - 验证命令: pytest tests/test_order_regression.py
  - 验证证据: pending
  - 依赖: B-002
  - 风险: medium
  - 覆盖: SAFE-001
  - 可并行: 否
  - 验证标准：证明修复未影响正常下单流程
```

**智能体输出：**

> Bugfix 规范工件已生成。请审查 `<specs_dir>/bugfix.md`、`<specs_dir>/design.md`、`<specs_dir>/tasks.md`、`<specs_dir>/progress.md` 和 `<specs_dir>/spec.yml`。
> 通过校验仍不代表批准实施。确认无误后，请回复 `批准规范，启动执行`。
>
> 兼容旧短语：`批准 bugfix 规范，启动执行`。
>
> ```bash
> python plugins/spec-workflow/scripts/validate_spec.py <specs_dir> --workflow bugfix
> python plugins/spec-workflow/scripts/spec_progress.py init <specs_dir>
> python plugins/spec-workflow/scripts/validate_spec.py <specs_dir> --resume
> ```

**用户回复：**

> 批准规范，启动执行

---

### 受控实施

**智能体：**

> 已收到批准，先冻结已批准 bugfix 规范、修复设计和任务计划基线。

```bash
python plugins/spec-workflow/scripts/spec_progress.py approve <specs_dir> --evidence "批准规范，启动执行"
```

> 锁定任务 B-001：建立重复消费导致双扣库存的失败证明。

智能体先记录断点，再写失败证明，不直接跳到修复：

```bash
python plugins/spec-workflow/scripts/spec_progress.py start <specs_dir> B-001
```

验证证据稳定后，通过受控工具更新状态：

```bash
python plugins/spec-workflow/scripts/spec_progress.py complete <specs_dir> B-001 --evidence "pytest tests/test_inventory_retry.py fails on unfixed code"
```

若实现 B-001 时发现原根因判断不成立，必须停止代码工作，运行 `sync-check --write` 标记 `reapproval-required`，回到 State B 更新 `bugfix.md`、`design.md` 或任务计划，并等待新的批准短语后重新运行 `approve`。

---

## 关键要点

1. Bugfix 先证明错误行为，再做最小修复。
2. `tasks.md` 使用 `B-xxx` 任务编号。
3. 不能用症状补丁掩盖根因，也不能削弱测试凑过验证。
4. 根因或范围变化必须回炉、标记 `reapproval-required`、重新批准并重新 `approve`。
5. 批准后 `bugfix.md`、`design.md` 和任务计划被冻结；任务开始/完成只能用 `spec_progress.py` 或 MCP 工具更新进度字段、`progress.md` 和 `spec.yml`。
