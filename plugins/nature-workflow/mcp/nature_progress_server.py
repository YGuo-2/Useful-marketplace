#!/usr/bin/env python3
"""Minimal stdio MCP server for Nature workflow progress tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from nature_progress import (  # noqa: E402
    DEFAULT_ROOT,
    NatureProgressError,
    command_block,
    command_complete,
    command_discover,
    command_log_note,
    command_new_workflow,
    command_resume,
    command_spec,
    command_start,
    command_status,
)
from nature_memory import (  # noqa: E402
    command_memory_check,
    command_memory_index,
    command_memory_list,
    command_memory_touch,
)


WORKFLOW_INPUTS = {
    "workflow_root": {"type": "string"},
    "project_root": {"type": "string"},
    "workflow_dir": {"type": "string"},
}


TOOLS = [
    {
        "name": "nature_new_workflow",
        "description": "Create a lightweight Nature workflow under a workflow root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "tasks": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "nature_discover_workflows",
        "description": "List Nature workflow directories under a workflow root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
            },
        },
    },
    {
        "name": "nature_status",
        "description": "Return workflow status, task counts, current task, and files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
            },
        },
    },
    {
        "name": "nature_resume",
        "description": "Return resumable state for a Nature workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
            },
        },
    },
    {
        "name": "nature_start_task",
        "description": "Mark a workflow task active.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
                "task_id": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "nature_complete_task",
        "description": "Mark a workflow task complete with evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
                "task_id": {"type": "string"},
                "evidence": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["task_id", "evidence"],
        },
    },
    {
        "name": "nature_block_task",
        "description": "Record a blocker for a workflow task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
                "task_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["task_id", "reason"],
        },
    },
    {
        "name": "nature_log_note",
        "description": "Append a human-readable note to a Nature workflow log.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
                "task_id": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["note"],
        },
    },
    {
        "name": "nature_spec",
        "description": "Record the optional format-spec gate decision (unset/skipped/ready) for a Nature workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
                "project_root": {"type": "string"},
                "workflow_dir": {"type": "string"},
                "status": {"type": "string", "enum": ["unset", "skipped", "ready"]},
                "source": {"type": "string", "enum": ["template", "dictation"]},
                "path": {"type": "string"},
            },
            "required": ["status"],
        },
    },
    {
        "name": "nature_memory_check",
        "description": "Validate a Nature workflow memory.md against project-memory rules.",
        "inputSchema": {
            "type": "object",
            "properties": WORKFLOW_INPUTS,
        },
    },
    {
        "name": "nature_memory_touch",
        "description": "Refresh one memory.md entry timestamp from the system clock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **WORKFLOW_INPUTS,
                "entry_id": {"type": "string"},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "nature_memory_index",
        "description": "Rewrite the project AGENTS.md Nature memory sentinel index.",
        "inputSchema": {
            "type": "object",
            "properties": WORKFLOW_INPUTS,
        },
    },
    {
        "name": "nature_memory_list",
        "description": "List memory.md entry summaries for a Nature workflow.",
        "inputSchema": {
            "type": "object",
            "properties": WORKFLOW_INPUTS,
        },
    },
]


def response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return payload


def text_result(data: Any) -> dict[str, Any]:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def _root(args: dict[str, Any]) -> str:
    raw = args.get("workflow_root", DEFAULT_ROOT)
    if raw is None:
        return DEFAULT_ROOT
    if not isinstance(raw, str):
        raise NatureProgressError("workflow_root must be a string")
    return raw


def _base(args: dict[str, Any]) -> Path | None:
    raw = args.get("project_root")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise NatureProgressError("project_root must be a string")
    return Path(raw).expanduser().resolve(strict=False)


def _workflow(args: dict[str, Any]) -> str | None:
    raw = args.get("workflow_dir")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise NatureProgressError("workflow_dir must be a string")
    return raw


def _tasks(args: dict[str, Any]) -> list[str] | None:
    raw = args.get("tasks")
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise NatureProgressError("tasks must be an array of strings")
    return raw


def _required_string(args: dict[str, Any], name: str) -> str:
    raw = args.get(name)
    if not isinstance(raw, str) or not raw.strip():
        raise NatureProgressError(f"{name} is required")
    return raw


def call_tool(name: str, args: dict[str, Any]) -> Any:
    base = _base(args)
    if name == "nature_new_workflow":
        return command_new_workflow(_root(args), args.get("slug"), args.get("title"), _tasks(args), base=base)
    if name == "nature_discover_workflows":
        return command_discover(_root(args), base=base)
    if name == "nature_status":
        return command_status(_root(args), _workflow(args), base=base)
    if name == "nature_resume":
        return command_resume(_root(args), _workflow(args), base=base)
    if name == "nature_start_task":
        return command_start(_root(args), _workflow(args), _required_string(args, "task_id"), base=base)
    if name == "nature_complete_task":
        return command_complete(
            _root(args),
            _workflow(args),
            _required_string(args, "task_id"),
            _required_string(args, "evidence"),
            args.get("notes", "") if isinstance(args.get("notes", ""), str) else "",
            base=base,
        )
    if name == "nature_block_task":
        return command_block(
            _root(args),
            _workflow(args),
            _required_string(args, "task_id"),
            _required_string(args, "reason"),
            base=base,
        )
    if name == "nature_log_note":
        return command_log_note(_root(args), _workflow(args), _required_string(args, "note"), args.get("task_id"), base=base)
    if name == "nature_spec":
        return command_spec(
            _root(args),
            _workflow(args),
            _required_string(args, "status"),
            args.get("source") or None,
            args.get("path") or None,
            base=base,
        )
    if name == "nature_memory_check":
        return command_memory_check(_root(args), _workflow(args), base=base)
    if name == "nature_memory_touch":
        return command_memory_touch(_root(args), _workflow(args), _required_string(args, "entry_id"), base=base)
    if name == "nature_memory_index":
        return command_memory_index(_root(args), _workflow(args), base=base, all_workflows=_workflow(args) is None)
    if name == "nature_memory_list":
        return command_memory_list(_root(args), _workflow(args), base=base)
    raise NatureProgressError(f"Unknown tool: {name}")


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "nature-workflow-progress", "version": "0.1.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params", {})
        try:
            result = call_tool(params.get("name", ""), params.get("arguments", {}) or {})
            return response(request_id, text_result(result))
        except NatureProgressError as exc:
            return response(request_id, error={"code": -32000, "message": str(exc)})
    return response(request_id, error={"code": -32601, "message": f"Unknown method: {method}"})


def main() -> int:
    # MCP stdio is UTF-8 by spec, but Windows pipes/consoles default to a locale
    # codec that mangles non-ASCII (e.g. Chinese) task titles — decode errors on
    # the way in, encode errors on the way out. Force UTF-8 on both streams.
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id = None
        try:
            message = json.loads(line)
            if isinstance(message, dict):
                request_id = message.get("id")
            reply = handle(message)
            if reply is not None:
                print(json.dumps(reply, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32099, "message": str(exc)},
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
