#!/usr/bin/env python3
"""Regression tests for the Spec Coding validator."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
TEMPLATES = PLUGIN_ROOT / "assets" / "templates"
VALIDATOR = SCRIPT_DIR / "validate_spec.py"


def run_validator(specs_dir: Path, workflow: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(specs_dir), "--workflow", workflow],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=merged_env,
    )


def write(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def valid_product() -> str:
    return """
    # 产品规范

    ## 用户故事与验收标准

    ### US-001: Publish comments

    #### 验收标准

    - **GIVEN** a signed-in reader is viewing a post
    - **WHEN** the reader submits a non-empty comment
    - **THEN** the comment is saved and shown in the comment list

    ## 非功能性需求

    | ID | 类别 | 描述 | 标准 |
    |:---|:---|:---|:---|
    | NFR-001 | 安全 | Comments require authentication | Auth is enforced |
    """


def valid_architecture() -> str:
    return """
    # 技术架构

    ## 数据模型

    The Comment entity stores post id, author id, body, and timestamps.

    ## API / 接口

    POST /comments creates a comment for an authenticated user.

    ## Dependencies

    No new dependency is required.

    ## Error Handling

    Invalid input returns a validation error.

    ## Security

    Authorization requires a signed-in user.

    ```mermaid
    flowchart TD
        Request --> Service
        Service --> Store
    ```
    """


def valid_requirements() -> str:
    return """
    # 需求规范

    > **来源设计：** docs/specs/design.md

    ## 功能需求与验收标准

    ### REQ-001: Publish outbox event

    #### 验收标准

    - **GIVEN** an order has been created
    - **WHEN** the outbox worker processes pending records
    - **THEN** an order-created event is published

    ## 非功能性需求

    | ID | 类别 | 描述 | 来源设计约束 |
    |:---|:---|:---|:---|
    | NFR-001 | 可靠性 | Events are retried | Derived from design.md |

    ## 设计映射

    REQ-001 is derived from design.md section 4.
    """


def valid_design(level: str = "High Level Design", include_lld: bool = True) -> str:
    lld = ""
    if include_lld:
        lld = """
        ## Low Level Design 细节

        - **模块 / 类职责：** Worker coordinates event publishing.
        - **函数签名与契约：** publish_event(order_id) returns a publish result.
        - **算法流程：** Load pending event, publish it, then mark it complete.
        - **状态转换：** Pending moves to Published after successful delivery.
        - **详细数据结构：** Outbox record contains id, payload, status, and retry count.
        """

    return f"""
    # 技术设计规范

    > **设计粒度：** {level}

    ## 设计起点与约束

    Existing order creation must keep its interface stable.

    ## 目标系统边界

    The changed 组件 are the order service and outbox worker.

    ## 方案设计

    The API writes an outbox row and the worker publishes it through the message bus.

    ```mermaid
    flowchart TD
        API --> Store
        Store --> Worker
        Worker --> Broker
    ```

    ## 备选方案与取舍

    Alternative direct publish was rejected because transaction consistency is weaker.

    ## 风险与验证策略

    Risk is duplicate delivery; Validation covers retry and idempotency behavior.

    {lld}
    """


def valid_design_tasks() -> str:
    return """
    # Design-First Tasks

    ## 执行规则

    1. Inline examples like `- [ ]`, `- [x]`, and `- [~]` are not tasks.

    ## 阶段 1

    - [ ] **T-001:** Implement the design.md persistence boundary
      - 验证标准: Design constraints are covered by tests
    """


def valid_feature_tasks() -> str:
    return """
    # Tasks

    ## 执行规则

    1. Inline examples like `- [ ]`, `- [x]`, and `- [~]` are not tasks.

    ## 阶段 1

    - [ ] **T-001:** Implement comment storage
      - 验证标准: Unit tests pass

    - [x] **T-002:** Record completed setup
      - 验证标准: Completion evidence is recorded

    - [~] **T-003:** Human-approved skip for optional export
      - 验证标准: Skip approval is recorded
    """


def valid_bugfix() -> str:
    return """
    # Bugfix Spec

    ## 证据与复现

    Evidence shows duplicate processing.

    ## 当前错误行为

    ### BUG-001: Duplicate deduction

    - **WHEN** the same order message is processed twice
    - **THEN** current behavior deducts inventory twice

    ## 修复后的期望行为

    ### FIX-001: Idempotent deduction

    - **WHEN** the same order message is processed twice
    - **THEN** inventory is deducted once

    ## 必须保持不变的行为

    ### SAFE-001: Normal order behavior

    - **WHEN** one valid order is submitted
    - **THEN** the original response contract remains unchanged

    ## 范围与约束

    The fix is limited to the inventory deduction path.
    """


def valid_bugfix_design() -> str:
    return """
    # Bugfix Design

    ## 根因分析 / Root Cause

    The retry consumer lacks an idempotency check.

    ## 代码路径与影响面

    The affected Surface is the retry consumer and inventory repository.

    ## 修复策略

    The Fix Strategy is to guard deduction by order id.

    ## 测试与验证策略

    Regression tests cover duplicate and normal single-order behavior.

    ## 风险与发布计划

    Rollout risk is low and rollback removes the guard.

    ```mermaid
    flowchart TD
        Retry --> Guard
        Guard --> Inventory
    ```
    """


def valid_bugfix_tasks(prefix: str = "B") -> str:
    return f"""
    # Bugfix Tasks

    ## 阶段 1

    - [ ] **{prefix}-001:** 建立复现失败证明
      - 验证标准: 复现测试稳定失败

    - [ ] **{prefix}-002:** 实现最小修复
      - 验证标准: 复现测试转为通过

    - [ ] **{prefix}-003:** 补充回归防护
      - 验证标准: 回归测试证明不变行为未破坏
    """


def make_requirements_first(specs_dir: Path, product: str | None = None, tasks: str | None = None) -> None:
    write(specs_dir / "product.md", product or valid_product())
    write(specs_dir / "architecture.md", valid_architecture())
    write(specs_dir / "tasks.md", tasks or valid_feature_tasks())


def make_design_first(specs_dir: Path, design: str | None = None) -> None:
    write(specs_dir / "design.md", design or valid_design())
    write(specs_dir / "requirements.md", valid_requirements())
    write(specs_dir / "tasks.md", valid_design_tasks())


def make_bugfix(specs_dir: Path, tasks: str | None = None) -> None:
    write(specs_dir / "bugfix.md", valid_bugfix())
    write(specs_dir / "design.md", valid_bugfix_design())
    write(specs_dir / "tasks.md", tasks or valid_bugfix_tasks())


class ValidatorRegressionTests(unittest.TestCase):
    def test_raw_templates_fail_for_all_workflows(self) -> None:
        cases = [
            (
                "requirements-first",
                {
                    "product_template.md": "product.md",
                    "architecture_template.md": "architecture.md",
                    "tasks_template.md": "tasks.md",
                },
            ),
            (
                "design-first",
                {
                    "design_first_design_template.md": "design.md",
                    "requirements_template.md": "requirements.md",
                    "design_first_tasks_template.md": "tasks.md",
                },
            ),
            (
                "bugfix",
                {
                    "bugfix_template.md": "bugfix.md",
                    "bugfix_design_template.md": "design.md",
                    "bugfix_tasks_template.md": "tasks.md",
                },
            ),
        ]

        for workflow, mapping in cases:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as tmp:
                specs_dir = Path(tmp)
                for source, target in mapping.items():
                    shutil.copyfile(TEMPLATES / source, specs_dir / target)

                result = run_validator(specs_dir, workflow)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("占位符", result.stdout)
                self.assertRegex(result.stdout, r"\.md:\d+")

    def test_prose_gwt_words_do_not_count_as_acceptance_criteria(self) -> None:
        prose_product = """
        # Product

        ## 用户故事

        ### US-001: Prose only

        This prose says given enough time users decide when to act and then expect output.

        ## 非功能性需求

        NFR-001: Fast enough.
        """
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_requirements_first(specs_dir, product=prose_product)

            result = run_validator(specs_dir, "requirements-first")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("缺少正式 GWT 行", result.stdout)

    def test_task_count_ignores_inline_checkbox_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_requirements_first(specs_dir)

            result = run_validator(specs_dir, "requirements-first")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("tasks.md 包含 3 个任务 (待完成: 1, 已完成: 1, 已跳过: 1)", result.stdout)

    def test_bugfix_rejects_t_prefixed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_bugfix(specs_dir, tasks=valid_bugfix_tasks(prefix="T"))

            result = run_validator(specs_dir, "bugfix")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("B-xxx", result.stdout)

    def test_lld_markers_trigger_lld_depth_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_design_first(specs_dir, design=valid_design(level="详细设计", include_lld=False))

            result = run_validator(specs_dir, "design-first")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Low Level Design 模块", result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_design_first(specs_dir, design=valid_design(level="High Level Design", include_lld=False))

            result = run_validator(specs_dir, "design-first")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_valid_minimal_workflows_pass(self) -> None:
        makers = [
            ("requirements-first", make_requirements_first),
            ("design-first", make_design_first),
            ("bugfix", make_bugfix),
        ]

        for workflow, maker in makers:
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as tmp:
                specs_dir = Path(tmp)
                maker(specs_dir)

                result = run_validator(specs_dir, workflow)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_utf8_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_requirements_first(specs_dir)
            (specs_dir / "product.md").write_bytes(b"\xff\xfe\x00\x00")

            result = run_validator(specs_dir, "requirements-first")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("UTF-8", result.stdout)
            self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_no_color_environment_suppresses_ansi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            specs_dir = Path(tmp)
            make_requirements_first(specs_dir)

            result = run_validator(specs_dir, "requirements-first", env={"NO_COLOR": "1"})

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("\x1b[", result.stdout)


if __name__ == "__main__":
    unittest.main()
