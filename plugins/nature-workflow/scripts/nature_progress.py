#!/usr/bin/env python3
"""Stdlib-only state engine for lightweight Nature workflows."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = "docs/nature-workflows"
SCHEMA_VERSION = 1
TASK_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,31}$")


class NatureProgressError(Exception):
    """Raised for user-correctable workflow-state errors."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str | None, default: str = "nature-workflow") -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text or default)[:64].strip("-") or default


def base_dir() -> Path:
    return Path(os.environ.get("NATURE_WORKFLOW_BASE_DIR", os.getcwd())).resolve()


def _assert_within(path: Path, parent: Path, label: str) -> Path:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise NatureProgressError(f"{label} must stay within {parent}") from exc
    return path


def checked_root(root: str | None = None, *, base: Path | None = None) -> Path:
    base = (base or base_dir()).resolve()
    raw = root or DEFAULT_ROOT
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return _assert_within(path.resolve(strict=False), base, "workflow root")


def latest_workflow(root: Path) -> Path:
    if not root.exists():
        raise NatureProgressError(f"No workflow root exists at {root}")
    workflows = [p for p in root.iterdir() if p.is_dir() and (p / "nature.yml").exists()]
    if not workflows:
        raise NatureProgressError(f"No Nature workflows found under {root}")
    return sorted(workflows, key=lambda p: p.name)[-1]


def checked_workflow_dir(
    workflow: str | None = None,
    root: str | None = None,
    *,
    base: Path | None = None,
) -> Path:
    base = (base or base_dir()).resolve()
    root_path = checked_root(root, base=base)
    if not workflow:
        return latest_workflow(root_path)

    raw = Path(workflow).expanduser()
    candidates: list[Path]
    if raw.is_absolute():
        candidates = [raw]
    else:
        candidates = [root_path / raw, base / raw]

    chosen = next((p for p in candidates if (p / "nature.yml").exists()), candidates[0])
    resolved = chosen.resolve(strict=False)
    _assert_within(resolved, base, "workflow directory")
    _assert_within(resolved, root_path, "workflow directory")
    return resolved


def parse_tasks(task_texts: list[str] | None) -> list[dict[str, Any]]:
    texts = task_texts or [
        "Select the nature skill and collect inputs",
        "Run the nature skill workflow",
        "Verify outputs and record notes",
    ]
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(texts, start=1):
        text = raw.strip()
        if not text:
            continue
        task_id = f"T{index}"
        title = text
        match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_.-]{0,31})\s*[:|]\s*(.+)$", text)
        if match:
            task_id = match.group(1)
            title = match.group(2).strip()
        if not TASK_ID_RE.match(task_id):
            raise NatureProgressError(f"Invalid task id: {task_id}")
        if task_id in seen:
            raise NatureProgressError(f"Duplicate task id: {task_id}")
        if not title:
            raise NatureProgressError(f"Task {task_id} is missing a title")
        seen.add(task_id)
        tasks.append(
            {
                "id": task_id,
                "title": title,
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "blocked_at": None,
                "evidence": "",
                "blocker": "",
                "notes": "",
            }
        )
    if not tasks:
        raise NatureProgressError("At least one task is required")
    return tasks


def load_record(workflow_dir: Path) -> dict[str, Any]:
    state_path = workflow_dir / "nature.yml"
    if not state_path.exists():
        raise NatureProgressError(f"Missing nature.yml in {workflow_dir}")
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NatureProgressError(f"Invalid nature.yml JSON/YAML-compatible state: {exc}") from exc
    if not isinstance(data, dict):
        raise NatureProgressError("nature.yml must contain an object")
    return data


def save_record(workflow_dir: Path, record: dict[str, Any]) -> None:
    record["updated_at"] = now_utc()
    workflow_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        workflow_dir / "nature.yml",
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write_text(workflow_dir / "progress.md", render_progress(record))
    _atomic_write_text(workflow_dir / "tasks.md", render_tasks(record))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        newline="",
    ) as tmp:
        tmp.write(text)
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def find_task(record: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in record.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise NatureProgressError(f"Unknown task id: {task_id}")


def append_log(record: dict[str, Any], event: str, message: str, task_id: str | None = None) -> None:
    record.setdefault("log", []).append(
        {
            "at": now_utc(),
            "event": event,
            "task_id": task_id or "",
            "message": message,
        }
    )


def update_workflow_status(record: dict[str, Any]) -> None:
    tasks = record.get("tasks", [])
    if tasks and all(task.get("status") == "completed" for task in tasks):
        record["status"] = "completed"
        record["active_task"] = None
        return
    if any(task.get("status") == "blocked" for task in tasks):
        record["status"] = "blocked"
        blocked = next(task for task in tasks if task.get("status") == "blocked")
        record["active_task"] = blocked.get("id")
        return
    record["status"] = "open"


def summarize(record: dict[str, Any], workflow_dir: Path) -> dict[str, Any]:
    tasks = record.get("tasks", [])
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.get("status", "unknown")] = counts.get(task.get("status", "unknown"), 0) + 1
    next_task = next((task for task in tasks if task.get("status") in {"active", "blocked", "pending"}), None)
    return {
        "workflow_dir": str(workflow_dir),
        "title": record.get("title", ""),
        "slug": record.get("slug", ""),
        "status": record.get("status", "unknown"),
        "active_task": record.get("active_task"),
        "task_counts": counts,
        "next_task": next_task,
        "files": {
            "nature": str(workflow_dir / "nature.yml"),
            "progress": str(workflow_dir / "progress.md"),
            "tasks": str(workflow_dir / "tasks.md"),
        },
    }


def render_progress(record: dict[str, Any]) -> str:
    active = record.get("active_task") or "none"
    lines = [
        "# Nature Workflow Progress",
        "",
        f"- Title: {record.get('title', '')}",
        f"- Slug: {record.get('slug', '')}",
        f"- Status: {record.get('status', '')}",
        f"- Active task: {active}",
        f"- Created: {record.get('created_at', '')}",
        f"- Updated: {record.get('updated_at', '')}",
        "",
        "## Tasks",
        "",
    ]
    for task in record.get("tasks", []):
        lines.append(f"- {task.get('id')} [{task.get('status')}] {task.get('title')}")
        if task.get("evidence"):
            lines.append(f"  - Evidence: {task.get('evidence')}")
        if task.get("blocker"):
            lines.append(f"  - Blocker: {task.get('blocker')}")
        if task.get("notes"):
            lines.append(f"  - Notes: {task.get('notes')}")
    lines.extend(["", "## Log", ""])
    for item in record.get("log", []):
        task_part = f" {item.get('task_id')}" if item.get("task_id") else ""
        lines.append(f"- {item.get('at')} {item.get('event')}{task_part}: {item.get('message')}")
    return "\n".join(lines).rstrip() + "\n"


def render_tasks(record: dict[str, Any]) -> str:
    lines = ["# Nature Workflow Tasks", ""]
    for task in record.get("tasks", []):
        checked = "x" if task.get("status") == "completed" else " "
        lines.append(f"- [{checked}] {task.get('id')} - {task.get('title')}")
        lines.append(f"  - Status: {task.get('status')}")
        if task.get("blocker"):
            lines.append(f"  - Blocker: {task.get('blocker')}")
        if task.get("evidence"):
            lines.append(f"  - Evidence: {task.get('evidence')}")
    return "\n".join(lines).rstrip() + "\n"


def command_new_workflow(
    workflow_root: str | None = None,
    slug: str | None = None,
    title: str | None = None,
    tasks: list[str] | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    root = checked_root(workflow_root, base=base)
    root.mkdir(parents=True, exist_ok=True)
    clean_slug = slugify(slug or title)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    workflow_dir = root / f"{timestamp}-{clean_slug}"
    suffix = 2
    while workflow_dir.exists():
        workflow_dir = root / f"{timestamp}-{clean_slug}-{suffix}"
        suffix += 1
    created = now_utc()
    record = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created,
        "updated_at": created,
        "slug": clean_slug,
        "title": title or clean_slug.replace("-", " ").title(),
        "status": "open",
        "active_task": None,
        "tasks": parse_tasks(tasks),
        "log": [],
    }
    append_log(record, "new", "Workflow created")
    save_record(workflow_dir, record)
    return {"ok": True, "action": "new", **summarize(record, workflow_dir)}


def command_discover(workflow_root: str | None = None, *, base: Path | None = None) -> dict[str, Any]:
    root = checked_root(workflow_root, base=base)
    workflows: list[dict[str, Any]] = []
    if root.exists():
        for item in sorted(root.iterdir(), key=lambda p: p.name):
            if not item.is_dir() or not (item / "nature.yml").exists():
                continue
            record = load_record(item)
            workflows.append(summarize(record, item))
    return {"ok": True, "action": "discover", "workflow_root": str(root), "workflows": workflows}


def command_status(
    workflow_root: str | None = None,
    workflow: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    update_workflow_status(record)
    return {"ok": True, "action": "status", **summarize(record, workflow_dir), "tasks": record.get("tasks", [])}


def command_resume(
    workflow_root: str | None = None,
    workflow: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    update_workflow_status(record)
    summary = summarize(record, workflow_dir)
    if record.get("status") == "blocked":
        resume_state = "blocked"
    elif record.get("status") == "completed":
        resume_state = "completed"
    else:
        resume_state = "ready"
    return {"ok": True, "action": "resume", "resume_state": resume_state, **summary}


def command_start(
    workflow_root: str | None,
    workflow: str | None,
    task_id: str,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    task = find_task(record, task_id)
    if task.get("status") == "completed":
        raise NatureProgressError(f"Task {task_id} is already completed")
    active = next((item for item in record.get("tasks", []) if item.get("status") == "active"), None)
    if active and active.get("id") != task_id:
        raise NatureProgressError(f"Task {active.get('id')} is already active")
    task["status"] = "active"
    task["started_at"] = task.get("started_at") or now_utc()
    task["blocked_at"] = None
    task["blocker"] = ""
    record["status"] = "open"
    record["active_task"] = task_id
    append_log(record, "start", "Task started", task_id)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "start", **summarize(record, workflow_dir)}


def command_complete(
    workflow_root: str | None,
    workflow: str | None,
    task_id: str,
    evidence: str,
    notes: str = "",
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    if not evidence.strip():
        raise NatureProgressError("Completion evidence is required")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    task = find_task(record, task_id)
    task["status"] = "completed"
    task["completed_at"] = now_utc()
    task["evidence"] = evidence.strip()
    task["notes"] = notes.strip()
    task["blocker"] = ""
    task["blocked_at"] = None
    if record.get("active_task") == task_id:
        record["active_task"] = None
    append_log(record, "complete", evidence.strip(), task_id)
    update_workflow_status(record)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "complete", **summarize(record, workflow_dir)}


def command_block(
    workflow_root: str | None,
    workflow: str | None,
    task_id: str,
    reason: str,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise NatureProgressError("Block reason is required")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    task = find_task(record, task_id)
    if task.get("status") == "completed":
        raise NatureProgressError(f"Task {task_id} is already completed")
    active = next((item for item in record.get("tasks", []) if item.get("status") == "active"), None)
    if active and active.get("id") != task_id:
        raise NatureProgressError(f"Task {active.get('id')} is already active")
    task["status"] = "blocked"
    task["blocked_at"] = now_utc()
    task["blocker"] = reason.strip()
    record["status"] = "blocked"
    record["active_task"] = task_id
    append_log(record, "block", reason.strip(), task_id)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "block", **summarize(record, workflow_dir)}


def command_log_note(
    workflow_root: str | None,
    workflow: str | None,
    note: str,
    task_id: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    if not note.strip():
        raise NatureProgressError("Note is required")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    if task_id:
        find_task(record, task_id)
    append_log(record, "note", note.strip(), task_id)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "log", **summarize(record, workflow_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage lightweight Nature workflow state.")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create a new workflow directory.")
    new.add_argument("--root", default=DEFAULT_ROOT)
    new.add_argument("--slug", default="nature-workflow")
    new.add_argument("--title", default="")
    new.add_argument("--task", action="append", default=[])

    discover = sub.add_parser("discover", help="List workflow directories.")
    discover.add_argument("--root", default=DEFAULT_ROOT)

    status = sub.add_parser("status", help="Show workflow status.")
    status.add_argument("--root", default=DEFAULT_ROOT)
    status.add_argument("--workflow", default="")

    resume = sub.add_parser("resume", help="Return resumable workflow state.")
    resume.add_argument("--root", default=DEFAULT_ROOT)
    resume.add_argument("--workflow", default="")

    start = sub.add_parser("start", help="Mark a task active.")
    start.add_argument("task_id")
    start.add_argument("--root", default=DEFAULT_ROOT)
    start.add_argument("--workflow", default="")

    complete = sub.add_parser("complete", help="Mark a task complete.")
    complete.add_argument("task_id")
    complete.add_argument("--evidence", required=True)
    complete.add_argument("--notes", default="")
    complete.add_argument("--root", default=DEFAULT_ROOT)
    complete.add_argument("--workflow", default="")

    block = sub.add_parser("block", help="Mark a task blocked.")
    block.add_argument("task_id")
    block.add_argument("--reason", required=True)
    block.add_argument("--root", default=DEFAULT_ROOT)
    block.add_argument("--workflow", default="")

    log = sub.add_parser("log", help="Append a progress note.")
    log.add_argument("--note", required=True)
    log.add_argument("--task-id", default="")
    log.add_argument("--root", default=DEFAULT_ROOT)
    log.add_argument("--workflow", default="")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "new":
        return command_new_workflow(args.root, args.slug, args.title, args.task)
    if args.command == "discover":
        return command_discover(args.root)
    if args.command == "status":
        return command_status(args.root, args.workflow or None)
    if args.command == "resume":
        return command_resume(args.root, args.workflow or None)
    if args.command == "start":
        return command_start(args.root, args.workflow or None, args.task_id)
    if args.command == "complete":
        return command_complete(args.root, args.workflow or None, args.task_id, args.evidence, args.notes)
    if args.command == "block":
        return command_block(args.root, args.workflow or None, args.task_id, args.reason)
    if args.command == "log":
        return command_log_note(args.root, args.workflow or None, args.note, args.task_id or None)
    raise NatureProgressError(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        result = dispatch(parser.parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except NatureProgressError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
