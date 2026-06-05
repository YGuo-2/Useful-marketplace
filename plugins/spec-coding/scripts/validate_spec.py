#!/usr/bin/env python3
"""
Spec Coding 规范完整性验证脚本

支持三类工作流：
1. Feature / Requirements-First: product.md + architecture.md + tasks.md
2. Feature / Design-First: design.md + requirements.md + tasks.md
3. Bugfix: bugfix.md + design.md + tasks.md

用法:
    python validate_spec.py docs/specs/
    python validate_spec.py docs/specs/ --workflow requirements-first
    python validate_spec.py docs/specs/ --workflow design-first
    python validate_spec.py docs/specs/ --workflow bugfix
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


Result = tuple[bool, str]
COLOR_MODE = "auto"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class ValidationReadError(Exception):
    """Raised when a spec file cannot be read as UTF-8 text."""


@dataclass(frozen=True)
class TaskStats:
    unchecked: int
    checked: int
    skipped: int

    @property
    def total(self) -> int:
        return self.unchecked + self.checked + self.skipped


def set_color_mode(mode: str) -> None:
    global COLOR_MODE
    COLOR_MODE = mode


def should_colorize() -> bool:
    if COLOR_MODE == "always":
        return True
    if COLOR_MODE == "never" or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def colorize(text: str, color: str) -> str:
    if not should_colorize():
        return text
    return f"{color}{text}{Colors.RESET}"


def read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        filename = Path(path).name
        raise ValidationReadError(
            f"{filename} 不是有效 UTF-8 文本，请转换为 UTF-8 后重试 "
            f"(byte {exc.start}, reason: {exc.reason})"
        ) from exc
    except OSError as exc:
        filename = Path(path).name
        raise ValidationReadError(f"{filename} 读取失败: {exc}") from exc


def load_spec_file(specs_dir: str, filename: str) -> tuple[str | None, list[Result]]:
    filepath = Path(specs_dir) / filename
    if not filepath.is_file():
        return None, [(False, f"{filename} 不存在，跳过内容检查")]
    try:
        return read_text(filepath), []
    except ValidationReadError as exc:
        return None, [(False, str(exc))]


def check_file_exists(specs_dir: str, filename: str) -> Result:
    filepath = os.path.join(specs_dir, filename)
    if os.path.isfile(filepath):
        return True, f"文件存在: {filename}"
    return False, f"缺失文件: {filename}"


def has_pattern(content: str, pattern: str) -> bool:
    return bool(re.search(pattern, content, re.IGNORECASE | re.MULTILINE))


def normalize_workflow(workflow: str | None) -> str | None:
    aliases = {
        "feature": "requirements-first",
        "requirements-first": "requirements-first",
        "design-first": "design-first",
        "bugfix": "bugfix",
        "auto": "auto",
    }
    if workflow is None:
        return None
    return aliases.get(workflow)


def detect_workflow(specs_dir: str) -> str | None:
    has_requirements_first = all(
        os.path.isfile(os.path.join(specs_dir, filename))
        for filename in ("product.md", "architecture.md")
    )
    has_design_first = all(
        os.path.isfile(os.path.join(specs_dir, filename))
        for filename in ("design.md", "requirements.md")
    )
    has_bugfix = all(
        os.path.isfile(os.path.join(specs_dir, filename))
        for filename in ("bugfix.md", "design.md")
    )

    matches = [
        workflow
        for workflow, present in (
            ("requirements-first", has_requirements_first),
            ("design-first", has_design_first),
            ("bugfix", has_bugfix),
        )
        if present
    ]

    if len(matches) == 1:
        return matches[0]
    return None


def display_workflow(workflow: str) -> str:
    labels = {
        "requirements-first": "Feature / Requirements-First",
        "design-first": "Feature / Design-First",
        "bugfix": "Bugfix",
    }
    return labels[workflow]


def required_files_for(workflow: str) -> list[str]:
    return {
        "requirements-first": ["product.md", "architecture.md", "tasks.md"],
        "design-first": ["design.md", "requirements.md", "tasks.md"],
        "bugfix": ["bugfix.md", "design.md", "tasks.md"],
    }[workflow]


BRACKET_PLACEHOLDER_RE = re.compile(r"\[([^\]\n]{1,120})\]")
TODO_RE = re.compile(r"\b(?:TODO|FIXME|TBD)\b|待补充|待定", re.IGNORECASE)
DEFAULT_TEMPLATE_PATTERNS = [
    (re.compile(r"High Level Design\s*\|\s*Low Level Design", re.IGNORECASE), "未选择设计粒度"),
    (re.compile(r"草稿\s*\|\s*审查中\s*\|\s*已批准"), "未选择文档状态"),
    (re.compile(r"是\s*/\s*否"), "未替换是否选项"),
    (re.compile(r"采用\s*/\s*放弃"), "未替换方案结论"),
    (re.compile(r"批准/驳回/待修改"), "未替换审批决定"),
    (re.compile(r"AI Architect\s*\+\s*Human Engineer", re.IGNORECASE), "未替换默认作者"),
    (re.compile(r"请根据实际方案替换上图"), "未替换示例图提示"),
]


def is_ignored_bracket_token(line: str, match: re.Match[str]) -> bool:
    token = match.group(1).strip()
    if token in {"", "x", "X", "~"}:
        return True
    if match.end() < len(line) and line[match.end()] == "(":
        return True
    return False


def find_draft_residue(filename: str, content: str) -> list[str]:
    hits: list[str] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in BRACKET_PLACEHOLDER_RE.finditer(line):
            if is_ignored_bracket_token(line, match):
                continue
            hits.append(f"{filename}:{line_number} 方括号占位符 {match.group(0)}")
        if TODO_RE.search(line):
            hits.append(f"{filename}:{line_number} TODO/FIXME/TBD/待定残留")
        for pattern, description in DEFAULT_TEMPLATE_PATTERNS:
            if pattern.search(line):
                hits.append(f"{filename}:{line_number} {description}")
    return hits


def check_draft_residue(specs_dir: str, required_files: list[str]) -> list[Result]:
    results: list[Result] = []
    for filename in required_files:
        filepath = Path(specs_dir) / filename
        if not filepath.is_file():
            results.append((False, f"{filename} 不存在，跳过占位符检查"))
            continue
        try:
            content = read_text(filepath)
        except ValidationReadError as exc:
            results.append((False, str(exc)))
            continue

        hits = find_draft_residue(filename, content)
        if not hits:
            results.append((True, f"{filename} 未发现模板占位符或草稿残留"))
            continue

        preview = "; ".join(hits[:6])
        if len(hits) > 6:
            preview += f"; 另有 {len(hits) - 6} 处"
        results.append((False, f"{filename} 存在未替换占位符/草稿残留: {preview}"))
    return results


GWT_LINE_RE = re.compile(
    r"^\s*[-*]\s+(?:\*\*)?(GIVEN|WHEN|THEN)(?:\*\*)?\s*(?:[:：-])?\s+\S",
    re.IGNORECASE | re.MULTILINE,
)


def gwt_terms(content: str) -> set[str]:
    return {match.group(1).upper() for match in GWT_LINE_RE.finditer(content)}


def check_gwt_lines(content: str, filename: str, required_terms: tuple[str, ...]) -> Result:
    present = gwt_terms(content)
    missing = [term for term in required_terms if term not in present]
    if not missing:
        return True, f"{filename} 包含正式 {' / '.join(required_terms)} 验收/行为行"
    return (
        False,
        f"{filename} 缺少正式 GWT 行: {', '.join(missing)} "
        "(需使用类似 '- **GIVEN** ...' 的独立列表行)",
    )


def is_low_level_design(content: str) -> bool:
    for line in content.splitlines():
        if not re.search(r"设计粒度|Design Level|Design Granularity", line, re.IGNORECASE):
            continue
        if re.search(
            r"\bLow[- ]?Level Design\b|\bLLD\b|低层设计|详细设计",
            line,
            re.IGNORECASE,
        ):
            return True
    return False


def check_product_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "product.md")
    if content is None:
        return load_errors

    results: list[Result] = [check_gwt_lines(content, "product.md", ("GIVEN", "WHEN", "THEN"))]

    if has_pattern(content, r"US-\d+|用户故事|User Story"):
        results.append((True, "product.md 包含用户故事标识"))
    else:
        results.append((False, "product.md 缺少用户故事标识 (如 US-001)"))

    if has_pattern(content, r"非功能|NFR|Non-Functional"):
        results.append((True, "product.md 包含非功能性需求章节"))
    else:
        results.append((False, "product.md 缺少非功能性需求章节"))

    return results


def check_architecture_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "architecture.md")
    if content is None:
        return load_errors

    results: list[Result] = []
    required_sections = [
        (r"数据模型|Data Model|实体", "数据模型定义"),
        (r"API|接口|Interface|端点|Endpoint", "API / 接口签名"),
        (r"依赖|Dependency|Dependencies", "依赖清单"),
        (r"错误处理|Error Handling|异常", "错误处理策略"),
        (r"安全|Security|认证|Authorization", "安全策略"),
    ]

    for pattern, desc in required_sections:
        if has_pattern(content, pattern):
            results.append((True, f"architecture.md 包含: {desc}"))
        else:
            results.append((False, f"architecture.md 缺少: {desc}"))

    if "```mermaid" in content:
        results.append((True, "architecture.md 包含 Mermaid 图"))
    else:
        results.append((False, "architecture.md 缺少 Mermaid 图"))

    return results


def check_requirements_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "requirements.md")
    if content is None:
        return load_errors

    results: list[Result] = [check_gwt_lines(content, "requirements.md", ("GIVEN", "WHEN", "THEN"))]

    if has_pattern(content, r"REQ-\d+|需求|Requirement"):
        results.append((True, "requirements.md 包含需求标识"))
    else:
        results.append((False, "requirements.md 缺少需求标识 (如 REQ-001)"))

    if has_pattern(content, r"设计映射|来源设计|Derived from Design|design\.md"):
        results.append((True, "requirements.md 明确标注了设计来源"))
    else:
        results.append((False, "requirements.md 缺少设计来源或映射说明"))

    if has_pattern(content, r"非功能|NFR|Non-Functional"):
        results.append((True, "requirements.md 包含非功能性需求章节"))
    else:
        results.append((False, "requirements.md 缺少非功能性需求章节"))

    return results


def check_design_first_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "design.md")
    if content is None:
        return load_errors

    results: list[Result] = []
    required_sections = [
        (r"设计粒度|Design Level|High[- ]?Level Design|Low[- ]?Level Design|\bHLD\b|\bLLD\b|详细设计|低层设计", "设计粒度"),
        (r"设计起点|设计输入|约束|Constraint", "设计起点与约束"),
        (r"组件|边界|系统边界|Scope", "目标系统边界"),
        (r"方案设计|接口|数据流|Topology|调用链", "方案设计"),
        (r"备选方案|取舍|Alternative", "备选方案与取舍"),
        (r"风险|验证策略|Risk|Validation", "风险与验证策略"),
    ]

    for pattern, desc in required_sections:
        if has_pattern(content, pattern):
            results.append((True, f"design.md 包含: {desc}"))
        else:
            results.append((False, f"design.md 缺少: {desc}"))

    if "```mermaid" in content:
        results.append((True, "design.md 包含 Mermaid 设计图"))
    else:
        results.append((False, "design.md 缺少 Mermaid 设计图"))

    if is_low_level_design(content):
        lld_sections = [
            (r"模块\s*/\s*类职责|模块.*职责|module.*responsibilit|class.*responsibilit", "Low Level Design 模块 / 类职责"),
            (r"函数签名|function signature|函数.*契约|method signature", "Low Level Design 函数签名与契约"),
            (r"算法|algorithm", "Low Level Design 算法流程"),
            (r"状态转换|状态机|state transition|state machine", "Low Level Design 状态转换"),
            (r"详细数据结构|数据结构|detailed data structure", "Low Level Design 详细数据结构"),
        ]
        for pattern, desc in lld_sections:
            if has_pattern(content, pattern):
                results.append((True, f"design.md 包含: {desc}"))
            else:
                results.append((False, f"design.md 缺少: {desc}"))

    return results


def check_bugfix_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "bugfix.md")
    if content is None:
        return load_errors

    results: list[Result] = []
    required_sections = [
        (r"证据|Evidence|复现|Reproduction", "证据与复现"),
        (r"当前错误行为|Current Behavior|BUG-\d+", "当前错误行为"),
        (r"期望行为|Expected Behavior|FIX-\d+", "修复后的期望行为"),
        (r"保持不变|Unchanged Behavior|SAFE-\d+|Regression", "必须保持不变的行为"),
        (r"范围|Scope|约束|Guardrails", "范围与约束"),
    ]

    for pattern, desc in required_sections:
        if has_pattern(content, pattern):
            results.append((True, f"bugfix.md 包含: {desc}"))
        else:
            results.append((False, f"bugfix.md 缺少: {desc}"))

    results.append(check_gwt_lines(content, "bugfix.md", ("WHEN", "THEN")))
    return results


def check_bugfix_design_spec(specs_dir: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "design.md")
    if content is None:
        return load_errors

    results: list[Result] = []
    required_sections = [
        (r"根因|Root Cause|初始假设", "根因分析"),
        (r"路径|影响面|组件|Surface", "代码路径与影响面"),
        (r"修复策略|Fix Strategy|最小安全修复", "修复策略"),
        (r"测试|验证|Regression|复现证明|修复证明", "测试与验证策略"),
        (r"风险|回滚|发布|Rollout", "风险与发布计划"),
    ]

    for pattern, desc in required_sections:
        if has_pattern(content, pattern):
            results.append((True, f"design.md 包含: {desc}"))
        else:
            results.append((False, f"design.md 缺少: {desc}"))

    if "```mermaid" in content:
        results.append((True, "design.md 包含 Mermaid 路径图"))
    else:
        results.append((False, "design.md 缺少 Mermaid 路径图"))

    return results


def expected_task_prefix(workflow: str) -> str:
    return "B" if workflow == "bugfix" else "T"


def task_line_pattern(workflow: str) -> re.Pattern[str]:
    prefix = expected_task_prefix(workflow)
    return re.compile(
        rf"^\s*-\s+\[(?P<status>[ xX~])\]\s+(?:\*\*)?"
        rf"(?P<task_id>{prefix}-\d+)\s*[:：](?:\*\*)?",
        re.MULTILINE,
    )


def checkbox_line_pattern() -> re.Pattern[str]:
    return re.compile(r"^\s*-\s+\[[ xX~]\]\s+.+", re.MULTILINE)


def collect_task_stats(content: str, workflow: str) -> tuple[TaskStats, list[str]]:
    expected_re = task_line_pattern(workflow)
    valid_matches = list(expected_re.finditer(content))
    stats = TaskStats(
        unchecked=sum(1 for match in valid_matches if match.group("status") == " "),
        checked=sum(1 for match in valid_matches if match.group("status").lower() == "x"),
        skipped=sum(1 for match in valid_matches if match.group("status") == "~"),
    )

    invalid_lines: list[str] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not checkbox_line_pattern().match(line):
            continue
        if not expected_re.match(line):
            invalid_lines.append(f"tasks.md:{line_number} {line.strip()}")
    return stats, invalid_lines


def check_tasks_spec(specs_dir: str, workflow: str) -> list[Result]:
    content, load_errors = load_spec_file(specs_dir, "tasks.md")
    if content is None:
        return load_errors

    results: list[Result] = []
    stats, invalid_lines = collect_task_stats(content, workflow)
    task_label = f"{expected_task_prefix(workflow)}-xxx"

    if stats.total > 0:
        results.append((
            True,
            f"tasks.md 包含 {stats.total} 个任务 "
            f"(待完成: {stats.unchecked}, 已完成: {stats.checked}, 已跳过: {stats.skipped})",
        ))
    else:
        results.append((False, f"tasks.md 缺少带 {task_label} 编号的复选框任务"))

    if invalid_lines:
        preview = "; ".join(invalid_lines[:4])
        if len(invalid_lines) > 4:
            preview += f"; 另有 {len(invalid_lines) - 4} 行"
        results.append((False, f"tasks.md 存在未编号或错误编号的复选框任务行: {preview}"))
    else:
        results.append((True, f"tasks.md 所有复选框任务均使用 {task_label} 编号"))

    if has_pattern(content, r"验证标准|Validation|Test|测试|✅"):
        results.append((True, "tasks.md 包含验证标准"))
    else:
        results.append((False, "tasks.md 缺少验证标准"))

    if workflow == "design-first":
        if has_pattern(content, r"设计|Design|design\.md"):
            results.append((True, "tasks.md 体现了设计约束或设计来源"))
        else:
            results.append((False, "tasks.md 缺少设计约束或设计来源说明"))

    if workflow == "bugfix":
        if has_pattern(content, r"复现|Reproduction|失败证明"):
            results.append((True, "tasks.md 包含复现或失败证明任务"))
        else:
            results.append((False, "tasks.md 缺少复现或失败证明任务"))

        if has_pattern(content, r"回归|Regression|不变行为"):
            results.append((True, "tasks.md 包含回归防护任务"))
        else:
            results.append((False, "tasks.md 缺少回归防护任务"))

    return results


def print_section(title: str) -> None:
    print(colorize(f"\n── {title} ──", Colors.BOLD))


def print_result(result: Result) -> None:
    icon = colorize("✔", Colors.GREEN) if result[0] else colorize("✖", Colors.RED)
    print(f"  {icon} {result[1]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Spec Coding 规范完整性验证工具",
        epilog="用于验证 docs/specs/ 目录下的 Requirements-First、Design-First 或 Bugfix 工件。",
    )
    parser.add_argument("specs_dir", help="规范文件所在目录路径 (如 docs/specs/)")
    parser.add_argument(
        "--workflow",
        default="auto",
        metavar="{auto,requirements-first,design-first,bugfix}",
        help="指定要验证的规范分支，默认自动检测；兼容旧别名 feature",
    )
    parser.add_argument(
        "--color",
        default="auto",
        choices=("auto", "always", "never"),
        help="控制 ANSI 颜色输出，默认 auto；重定向或设置 NO_COLOR 时不输出颜色",
    )
    args = parser.parse_args()
    set_color_mode(args.color)

    print(colorize("\n╔══════════════════════════════════════════════╗", Colors.CYAN))
    print(colorize("║   Spec Coding 规范完整性验证                ║", Colors.CYAN))
    print(colorize("╚══════════════════════════════════════════════╝\n", Colors.CYAN))

    specs_dir = args.specs_dir
    if not os.path.isdir(specs_dir):
        print(colorize(f"✖ 目录不存在: {specs_dir}", Colors.RED))
        print("\n请先运行 Spec Coding 工作流生成规范文件。")
        sys.exit(1)

    workflow = normalize_workflow(args.workflow)
    if workflow is None:
        print(colorize(f"✖ 不支持的工作流: {args.workflow}", Colors.RED))
        print("请使用 --workflow requirements-first / design-first / bugfix，或省略以自动检测。")
        sys.exit(1)

    if workflow == "auto":
        workflow = detect_workflow(specs_dir)
        if workflow is None:
            print(colorize("✖ 无法自动确定工作流。", Colors.RED))
            print("请确认规范目录只包含一套工件，或使用 --workflow requirements-first / design-first / bugfix 显式指定。")
            sys.exit(1)

    required_files = required_files_for(workflow)

    print(f"📂 检查目录: {os.path.abspath(specs_dir)}")
    print(f"🧭 规范分支: {display_workflow(workflow)}\n")

    all_results: list[Result] = []

    print_section("文件存在性检查")
    for filename in required_files:
        result = check_file_exists(specs_dir, filename)
        all_results.append(result)
        print_result(result)

    print_section("占位符与草稿残留检查")
    for result in check_draft_residue(specs_dir, required_files):
        all_results.append(result)
        print_result(result)

    if workflow == "requirements-first":
        print_section("product.md 内容检查")
        for result in check_product_spec(specs_dir):
            all_results.append(result)
            print_result(result)

        print_section("architecture.md 内容检查")
        for result in check_architecture_spec(specs_dir):
            all_results.append(result)
            print_result(result)
    elif workflow == "design-first":
        print_section("design.md 内容检查")
        for result in check_design_first_spec(specs_dir):
            all_results.append(result)
            print_result(result)

        print_section("requirements.md 内容检查")
        for result in check_requirements_spec(specs_dir):
            all_results.append(result)
            print_result(result)
    else:
        print_section("bugfix.md 内容检查")
        for result in check_bugfix_spec(specs_dir):
            all_results.append(result)
            print_result(result)

        print_section("design.md 内容检查")
        for result in check_bugfix_design_spec(specs_dir):
            all_results.append(result)
            print_result(result)

    print_section("tasks.md 内容检查")
    for result in check_tasks_spec(specs_dir, workflow):
        all_results.append(result)
        print_result(result)

    passed = sum(1 for ok, _ in all_results if ok)
    failed = len(all_results) - passed

    print(colorize("\n══════════════════════════════════════════════", Colors.CYAN))
    print(
        f"  总计: {len(all_results)} 项检查 | "
        f"{colorize(f'{passed} 通过', Colors.GREEN)} | "
        f"{colorize(f'{failed} 失败', Colors.RED)}"
    )

    if failed == 0:
        print(colorize("\n  ✅ 规范结构/内容完整性检查通过。进入代码实施阶段仍需用户批准短语。\n", Colors.GREEN))
        sys.exit(0)

    print(colorize(f"\n  ⚠️  存在 {failed} 项问题，请检查并修复后重新验证。\n", Colors.YELLOW))
    sys.exit(1)


if __name__ == "__main__":
    main()
