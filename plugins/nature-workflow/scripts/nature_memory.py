#!/usr/bin/env python3
"""Stdlib-only project memory engine for lightweight Nature workflows."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nature_progress import (  # noqa: E402
    DEFAULT_ROOT,
    NatureProgressError,
    _assert_within,
    _atomic_write_text,
    base_dir,
    checked_root,
    checked_workflow_dir,
    now_utc,
)


MEMORY_FILE = "memory.md"
MAX_BODY_CHARS = 280
MAX_BODY_LINES = 4
MAX_ENTRIES = 12
MAX_TITLE_CHARS = 40
SENTINEL_START = "<!-- NATURE-WORKFLOW-MEMORY-INDEX:START -->"
SENTINEL_END = "<!-- NATURE-WORKFLOW-MEMORY-INDEX:END -->"
ENTRY_RE = re.compile(r"^## M(?P<num>[1-9]\d*) · (?P<title>.+?)\s*$")
TS_RE = re.compile(r"^<!-- updated: (?P<updated>.+?) -->$")
ENTRY_LIKE_RE = re.compile(r"^#+\s*M[1-9]\d*\b")
PLACEHOLDER_TS_RE = re.compile(
    r"(YYYY|MM|DD|HH|TODO|TBD|FIXME|<[^>]+>|\{\{[^}]+\}\})",
    re.IGNORECASE,
)
FUTURE_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class Entry:
    entry_id: str
    title: str
    updated: str | None
    body: str
    body_lines: list[str]
    line: int
    timestamp_line: int | None


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _candidate_heading_indices(lines: list[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if line.lstrip().startswith("##")]


def parse_memory(text: str) -> list[Entry]:
    """Parse valid memory entries from memory.md text."""
    lines = text.splitlines()
    headings = _candidate_heading_indices(lines)
    entries: list[Entry] = []
    for pos, index in enumerate(headings):
        match = ENTRY_RE.fullmatch(lines[index])
        if not match:
            continue
        end = headings[pos + 1] if pos + 1 < len(headings) else len(lines)
        updated: str | None = None
        timestamp_line: int | None = None
        body_start = index + 1
        if index + 1 < end:
            ts_match = TS_RE.fullmatch(lines[index + 1])
            if ts_match:
                updated = ts_match.group("updated")
                timestamp_line = index + 2
                body_start = index + 2
            elif lines[index + 1].strip().startswith("<!-- updated:"):
                timestamp_line = index + 2
                body_start = index + 2
        body_lines = _trim_blank_lines(lines[body_start:end])
        entries.append(
            Entry(
                entry_id=f"M{match.group('num')}",
                title=match.group("title").strip(),
                updated=updated,
                body="\n".join(body_lines),
                body_lines=body_lines,
                line=index + 1,
                timestamp_line=timestamp_line,
            )
        )
    return entries


def _memory_path(workflow_dir: Path) -> Path:
    return workflow_dir / MEMORY_FILE


def _normalize_entry_id(entry_id: str) -> str:
    raw = entry_id.strip()
    match = re.fullmatch(r"M?([1-9]\d*)", raw)
    if not match:
        raise NatureProgressError("entry_id must look like M3 or 3")
    return f"M{match.group(1)}"


def _parse_updated(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _violation(
    entry: str,
    rule: str,
    detail: str,
    line: int | None,
    path: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "entry": entry,
        "rule": rule,
        "detail": detail,
        "line": line,
    }
    if path is not None:
        result["path"] = str(path)
    return result


def _check_text(text: str, *, path: Path | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    lines = text.splitlines()
    violations: list[dict[str, Any]] = []
    now = now or datetime.now(timezone.utc)

    for index, line in enumerate(lines):
        if not ENTRY_LIKE_RE.match(line) and not line.lstrip().startswith("##"):
            continue
        if not ENTRY_RE.fullmatch(line):
            violations.append(
                _violation(
                    "",
                    "title_format",
                    "Title must match '## M<integer> · <title>' with no leading whitespace.",
                    index + 1,
                    path,
                )
            )

    entries = parse_memory(text)
    if len(entries) > MAX_ENTRIES:
        violations.append(
            _violation(
                "",
                "max_entries",
                f"memory.md has {len(entries)} entries; maximum is {MAX_ENTRIES}.",
                None,
                path,
            )
        )

    seen: dict[str, int] = {}
    for entry in entries:
        if entry.entry_id in seen:
            violations.append(
                _violation(
                    entry.entry_id,
                    "duplicate_id",
                    f"{entry.entry_id} duplicates line {seen[entry.entry_id]}.",
                    entry.line,
                    path,
                )
            )
        else:
            seen[entry.entry_id] = entry.line

        if len(entry.title) > MAX_TITLE_CHARS:
            violations.append(
                _violation(
                    entry.entry_id,
                    "title_length",
                    f"Title has {len(entry.title)} characters; maximum is {MAX_TITLE_CHARS}.",
                    entry.line,
                    path,
                )
            )

        if entry.updated is None:
            if entry.timestamp_line is None:
                violations.append(
                    _violation(
                        entry.entry_id,
                        "timestamp_missing",
                        "The line immediately after the title must be '<!-- updated: <ISO8601 UTC> -->'.",
                        entry.line + 1,
                        path,
                    )
                )
            else:
                raw = lines[entry.timestamp_line - 1] if entry.timestamp_line - 1 < len(lines) else ""
                rule = "timestamp_placeholder" if PLACEHOLDER_TS_RE.search(raw) else "timestamp_invalid"
                violations.append(
                    _violation(
                        entry.entry_id,
                        rule,
                        "Timestamp line is not a concrete parseable ISO8601 UTC value.",
                        entry.timestamp_line,
                        path,
                    )
                )
        else:
            if PLACEHOLDER_TS_RE.search(entry.updated):
                violations.append(
                    _violation(
                        entry.entry_id,
                        "timestamp_placeholder",
                        "Timestamp must be generated by the script, not left as a placeholder.",
                        entry.timestamp_line,
                        path,
                    )
                )
            else:
                try:
                    parsed = _parse_updated(entry.updated)
                except ValueError:
                    violations.append(
                        _violation(
                            entry.entry_id,
                            "timestamp_invalid",
                            "Timestamp must be parseable by datetime.fromisoformat and include timezone.",
                            entry.timestamp_line,
                            path,
                        )
                    )
                else:
                    if parsed > now + FUTURE_TOLERANCE:
                        violations.append(
                            _violation(
                                entry.entry_id,
                                "timestamp_future",
                                "Timestamp is too far in the future for the current system clock.",
                                entry.timestamp_line,
                                path,
                            )
                        )

        if len(entry.body) > MAX_BODY_CHARS:
            violations.append(
                _violation(
                    entry.entry_id,
                    "body_chars",
                    f"Body has {len(entry.body)} characters; maximum is {MAX_BODY_CHARS}.",
                    entry.line,
                    path,
                )
            )
        if len(entry.body_lines) > MAX_BODY_LINES:
            violations.append(
                _violation(
                    entry.entry_id,
                    "body_lines",
                    f"Body has {len(entry.body_lines)} lines; maximum is {MAX_BODY_LINES}.",
                    entry.line,
                    path,
                )
            )

    return violations


def _workflow_dirs_with_memory(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        item for item in root.iterdir() if item.is_dir() and (item / MEMORY_FILE).exists()
    )


def _read_memory(workflow_dir: Path) -> str:
    path = _memory_path(workflow_dir)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _memory_summary(workflow_dir: Path) -> dict[str, Any]:
    path = _memory_path(workflow_dir)
    entries = parse_memory(_read_memory(workflow_dir))
    return {
        "workflow_dir": str(workflow_dir),
        "memory_path": str(path),
        "entries": [
            {
                "id": entry.entry_id,
                "title": entry.title,
                "updated": entry.updated,
                "line": entry.line,
            }
            for entry in entries
        ],
    }


def command_memory_check(
    workflow_root: str | None = None,
    workflow: str | None = None,
    *,
    base: Path | None = None,
    all_workflows: bool = False,
) -> dict[str, Any]:
    if all_workflows:
        root = checked_root(workflow_root, base=base)
        workflow_dirs = _workflow_dirs_with_memory(root)
    else:
        workflow_dirs = [checked_workflow_dir(workflow, workflow_root, base=base)]

    checked: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for workflow_dir in workflow_dirs:
        path = _memory_path(workflow_dir)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        entries = parse_memory(text)
        checked.append(
            {
                "workflow_dir": str(workflow_dir),
                "memory_path": str(path),
                "entries": len(entries),
            }
        )
        violations.extend(_check_text(text, path=path))

    return {
        "ok": not violations,
        "action": "memory_check",
        "checked": checked,
        "violations": violations,
    }


def command_memory_touch(
    workflow_root: str | None,
    workflow: str | None,
    entry_id: str,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    path = _memory_path(workflow_dir)
    if not path.exists():
        raise NatureProgressError(f"Missing {MEMORY_FILE} in {workflow_dir}")

    target_id = _normalize_entry_id(entry_id)
    lines = path.read_text(encoding="utf-8").splitlines()
    heading_index: int | None = None
    for index, line in enumerate(lines):
        match = ENTRY_RE.fullmatch(line)
        if match and f"M{match.group('num')}" == target_id:
            heading_index = index
            break
    if heading_index is None:
        raise NatureProgressError(f"Unknown memory entry: {target_id}")

    stamped = now_utc()
    updated_line = f"<!-- updated: {stamped} -->"
    next_index = heading_index + 1
    if next_index < len(lines) and lines[next_index].strip().startswith("<!-- updated:"):
        lines[next_index] = updated_line
        timestamp_line = next_index + 1
    else:
        lines.insert(next_index, updated_line)
        timestamp_line = next_index + 1
    _atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
    return {
        "ok": True,
        "action": "memory_touch",
        "workflow_dir": str(workflow_dir),
        "memory_path": str(path),
        "entry": target_id,
        "updated": stamped,
        "line": timestamp_line,
    }


def _entry_hook(entries: list[Entry]) -> str:
    if not entries:
        return "no project memory entries"
    return "; ".join(f"{entry.entry_id} {entry.title}" for entry in entries[:3])


def _resolve_agents_path(raw: str | None, *, base: Path) -> Path:
    path = Path(raw).expanduser() if raw else base / "AGENTS.md"
    if not path.is_absolute():
        path = base / path
    return _assert_within(path.resolve(strict=False), base, "AGENTS.md path")


def _replace_sentinel(existing: str, section: str) -> str:
    if SENTINEL_START in existing or SENTINEL_END in existing:
        start = existing.find(SENTINEL_START)
        end = existing.find(SENTINEL_END)
        if start == -1 or end == -1 or end < start:
            raise NatureProgressError("AGENTS.md has an incomplete Nature memory sentinel section")
        end += len(SENTINEL_END)
        return existing[:start].rstrip() + "\n\n" + section.rstrip() + "\n\n" + existing[end:].lstrip()
    if existing.strip():
        return existing.rstrip() + "\n\n" + section.rstrip() + "\n"
    return section.rstrip() + "\n"


def command_memory_index(
    workflow_root: str | None = None,
    workflow: str | None = None,
    *,
    base: Path | None = None,
    all_workflows: bool = True,
    agents_path: str | None = None,
) -> dict[str, Any]:
    project_root = (base or base_dir()).resolve()
    root = checked_root(workflow_root, base=project_root)
    if all_workflows:
        workflow_dirs = _workflow_dirs_with_memory(root)
    else:
        workflow_dirs = [checked_workflow_dir(workflow, workflow_root, base=project_root)]

    lines = [
        SENTINEL_START,
        "# Nature Workflow Memory Index",
        "",
        "Maintained by nature_memory.py. Edit workflow memory.md files, then run memory touch, check, and index.",
        "",
    ]
    indexed: list[dict[str, Any]] = []
    for workflow_dir in workflow_dirs:
        path = _memory_path(workflow_dir)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        violations = _check_text(text, path=path)
        if violations:
            raise NatureProgressError(f"{path} has memory check violations; run memory check first")
        entries = parse_memory(text)
        try:
            rel_memory = path.relative_to(project_root).as_posix()
        except ValueError:
            rel_memory = str(path)
        count = len(entries)
        noun = "entry" if count == 1 else "entries"
        hook = _entry_hook(entries)
        lines.append(f"- [{workflow_dir.name}]({rel_memory}): {count} {noun}; {hook}.")
        indexed.append(
            {
                "workflow_dir": str(workflow_dir),
                "memory_path": str(path),
                "entries": count,
                "hook": hook,
            }
        )
    if not indexed:
        lines.append("- No Nature workflow memory files found.")
    lines.append(SENTINEL_END)
    section = "\n".join(lines)

    agents = _resolve_agents_path(agents_path, base=project_root)
    existing = agents.read_text(encoding="utf-8") if agents.exists() else ""
    _atomic_write_text(agents, _replace_sentinel(existing, section))
    return {
        "ok": True,
        "action": "memory_index",
        "workflow_root": str(root),
        "agents_path": str(agents),
        "indexed": indexed,
    }


def command_memory_list(
    workflow_root: str | None = None,
    workflow: str | None = None,
    *,
    base: Path | None = None,
    all_workflows: bool = False,
) -> dict[str, Any]:
    if all_workflows:
        root = checked_root(workflow_root, base=base)
        workflows = _workflow_dirs_with_memory(root)
    else:
        workflows = [checked_workflow_dir(workflow, workflow_root, base=base)]
    return {
        "ok": True,
        "action": "memory_list",
        "workflows": [_memory_summary(workflow_dir) for workflow_dir in workflows],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Nature workflow project memory.")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument("--root", default=DEFAULT_ROOT)
        cmd.add_argument("--workflow", default="")
        cmd.add_argument("--base", default="")

    check = sub.add_parser("check", help="Validate memory.md rules.")
    common(check)
    check.add_argument("target", nargs="?")
    check.add_argument("--all", action="store_true")

    touch = sub.add_parser("touch", help="Refresh one entry timestamp from the system clock.")
    common(touch)
    touch.add_argument("entry_id")

    index = sub.add_parser("index", help="Rewrite the AGENTS.md memory sentinel index.")
    common(index)
    index.add_argument("target", nargs="?")
    index.add_argument("--all", action="store_true")
    index.add_argument("--agents-path", default="")

    list_cmd = sub.add_parser("list", help="List memory entries.")
    common(list_cmd)
    list_cmd.add_argument("target", nargs="?")
    list_cmd.add_argument("--all", action="store_true")
    return parser


def _base_from_args(args: argparse.Namespace) -> Path | None:
    return Path(args.base).expanduser().resolve(strict=False) if args.base else None


def _root_and_workflow_from_args(args: argparse.Namespace) -> tuple[str, str | None]:
    root = args.root
    workflow = args.workflow or None
    target = getattr(args, "target", None)
    if target:
        if getattr(args, "all", False):
            root = target
        else:
            workflow = target
    return root, workflow


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    base = _base_from_args(args)
    if args.command == "check":
        root, workflow = _root_and_workflow_from_args(args)
        return command_memory_check(root, workflow, base=base, all_workflows=args.all)
    if args.command == "touch":
        return command_memory_touch(args.root, args.workflow or None, args.entry_id, base=base)
    if args.command == "index":
        root, workflow = _root_and_workflow_from_args(args)
        all_workflows = args.all or workflow is None
        return command_memory_index(
            root,
            workflow,
            base=base,
            all_workflows=all_workflows,
            agents_path=args.agents_path or None,
        )
    if args.command == "list":
        root, workflow = _root_and_workflow_from_args(args)
        return command_memory_list(root, workflow, base=base, all_workflows=args.all)
    raise NatureProgressError(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "check" and not result.get("ok", False):
            return 2
        return 0
    except NatureProgressError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
