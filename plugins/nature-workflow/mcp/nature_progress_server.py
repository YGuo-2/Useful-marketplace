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
    command_start,
    command_status,
)


TOOLS = [
    {
        "name": "nature_new_workflow",
        "description": "Create a lightweight Nature workflow under a workflow root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
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
            "properties": {"workflow_root": {"type": "string"}},
        },
    },
    {
        "name": "nature_status",
        "description": "Return workflow status, task counts, current task, and files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_root": {"type": "string"},
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
                "workflow_dir": {"type": "string"},
                "task_id": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["note"],
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
    if name == "nature_new_workflow":
        return command_new_workflow(_root(args), args.get("slug"), args.get("title"), _tasks(args))
    if name == "nature_discover_workflows":
        return command_discover(_root(args))
    if name == "nature_status":
        return command_status(_root(args), _workflow(args))
    if name == "nature_resume":
        return command_resume(_root(args), _workflow(args))
    if name == "nature_start_task":
        return command_start(_root(args), _workflow(args), _required_string(args, "task_id"))
    if name == "nature_complete_task":
        return command_complete(
            _root(args),
            _workflow(args),
            _required_string(args, "task_id"),
            _required_string(args, "evidence"),
            args.get("notes", "") if isinstance(args.get("notes", ""), str) else "",
        )
    if name == "nature_block_task":
        return command_block(
            _root(args),
            _workflow(args),
            _required_string(args, "task_id"),
            _required_string(args, "reason"),
        )
    if name == "nature_log_note":
        return command_log_note(_root(args), _workflow(args), _required_string(args, "note"), args.get("task_id"))
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
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            reply = handle(message)
            if reply is not None:
                print(json.dumps(reply, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32099, "message": str(exc)},
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
