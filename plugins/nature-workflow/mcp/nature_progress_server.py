#!/usr/bin/env python3
"""Minimal stdio MCP server for Nature workflow progress tools."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SERVER_VERSION = os.environ.get("NATURE_WORKFLOW_VERSION", "0.2.0")
sys.path.insert(0, str(SCRIPT_DIR))

from nature_progress import (  # noqa: E402
    DEFAULT_ROOT,
    NatureProgressError,
    base_dir,
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
from nature_context import (  # noqa: E402
    block_with_memory_review,
    complete_with_memory_review,
    resume_with_memory,
)
from nature_memory import (  # noqa: E402
    command_memory_consolidate_apply,
    command_memory_consolidate_plan,
    command_memory_check,
    command_memory_forget,
    command_memory_index,
    command_memory_list,
    command_memory_migrate,
    command_memory_recall,
    command_memory_recall_all,
    command_memory_remember,
    command_memory_show,
    command_memory_supersede,
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
        "description": "Lint a Nature workflow memory file; entry count and byte thresholds are advisory signals.",
        "inputSchema": {
            "type": "object",
            "properties": {**WORKFLOW_INPUTS, "scope": {"type": "string", "enum": ["shared", "local"]}, "all_workflows": {"type": "boolean"}},
        },
    },
    {
        "name": "nature_memory_touch",
        "description": "Compatibility shim: refresh a legacy memory.md timestamp comment by unique title or alias.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **WORKFLOW_INPUTS,
                "entry_id": {"type": "string", "description": "Unique title or legacy alias to stamp."},
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
            "properties": {**WORKFLOW_INPUTS, "scope": {"type": "string", "enum": ["shared", "local"]}, "all_workflows": {"type": "boolean"}},
        },
    },
]


# These tools are appended to preserve the old Nature memory contract for one
# compatibility cycle while making mutation scope explicit for new callers.
TOOLS.extend(
    [
        {
            "name": "nature_memory_remember",
            "description": "Create or CAS-update one shared or local schema-v1 memory entry.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "metadata": {"type": "object"},
                    "entry_id": {"type": "string"},
                    "expected_etag": {"type": "string"},
                },
                "required": ["project_root", "workflow_dir", "scope", "title", "body", "metadata"],
            },
        },
        {
            "name": "nature_memory_recall",
            "description": "Recall bounded, deterministic low-trust memory context from one explicit scope.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
                    "max_bytes": {"type": "integer", "minimum": 256, "maximum": 4096},
                    "filters": {"type": "object"},
                    "all_workflows": {"type": "boolean"},
                },
                "required": ["project_root", "scope", "query"],
            },
        },
        {
            "name": "nature_memory_show",
            "description": "Show one stable memory entry and its derived successor locators.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "entry_id": {"type": "string"},
                },
                "required": ["project_root", "workflow_dir", "scope", "entry_id"],
            },
        },
        {
            "name": "nature_memory_forget",
            "description": "Archive one active memory entry with an ETag and reason.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "entry_id": {"type": "string"},
                    "expected_etag": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["project_root", "workflow_dir", "scope", "entry_id", "expected_etag", "reason"],
            },
        },
        {
            "name": "nature_memory_supersede",
            "description": "Replace one active entry with a successor in the same workflow and scope.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "old_id": {"type": "string"},
                    "expected_etag": {"type": "string"},
                    "new_title": {"type": "string"},
                    "new_body": {"type": "string"},
                    "new_metadata": {"type": "object"},
                },
                "required": ["project_root", "workflow_dir", "scope", "old_id", "expected_etag", "new_title", "new_body", "new_metadata"],
            },
        },
        {
            "name": "nature_memory_consolidate_plan",
            "description": "Build a deterministic, non-persistent consolidation plan.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_root", "workflow_dir", "scope", "source_ids"],
            },
        },
        {
            "name": "nature_memory_consolidate_apply",
            "description": "Apply a caller-provided consolidation body with full source CAS.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "plan_id": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                    "source_etags": {"type": ["object", "array"]},
                    "new_title": {"type": "string"},
                    "new_body": {"type": "string"},
                    "new_metadata": {"type": "object"},
                },
                "required": ["project_root", "workflow_dir", "scope", "plan_id", "source_ids", "source_etags", "new_title", "new_body", "new_metadata"],
            },
        },
        {
            "name": "nature_memory_migrate",
            "description": "Explicitly dry-run or migrate legacy memory entries, per workflow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "dry_run": {"type": "boolean"},
                    "all_workflows": {"type": "boolean"},
                },
                "required": ["project_root", "scope"],
                "allOf": [
                    {
                        "if": {"properties": {"all_workflows": {"const": True}}},
                        "then": {"not": {"required": ["workflow_dir"]}},
                        "else": {"required": ["workflow_dir"]},
                    }
                ],
            },
        },
        {
            "name": "nature_resume_with_memory",
            "description": "Resume progress and attach bounded memory context without coupling progress to memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "max_bytes": {"type": "integer"},
                },
                "required": ["project_root", "scope"],
            },
        },
        {
            "name": "nature_complete_with_memory_review",
            "description": "Commit progress completion first, then return a non-blocking memory review.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "task_id": {"type": "string"},
                    "evidence": {"type": "string"},
                    "notes": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "max_bytes": {"type": "integer"},
                },
                "required": ["project_root", "workflow_dir", "scope", "task_id", "evidence"],
            },
        },
        {
            "name": "nature_block_with_memory_review",
            "description": "Commit a progress blocker first, then return a non-blocking memory review.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {"type": "string"},
                    "workflow_root": {"type": "string"},
                    "workflow_dir": {"type": "string"},
                    "scope": {"type": "string", "enum": ["shared", "local"]},
                    "task_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "max_bytes": {"type": "integer"},
                },
                "required": ["project_root", "workflow_dir", "scope", "task_id", "reason"],
            },
        },
    ]
)


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


def _project_root_required(args: dict[str, Any]) -> Path:
    raw = args.get("project_root")
    if not isinstance(raw, str) or not raw.strip():
        raise NatureProgressError("project_root is required")
    return Path(raw).expanduser().resolve(strict=False)


def _required_scope(args: dict[str, Any]) -> str:
    scope = _required_string(args, "scope")
    if scope not in {"shared", "local"}:
        raise NatureProgressError("scope must be shared or local")
    return scope


def _required_object(args: dict[str, Any], name: str) -> dict[str, Any]:
    value = args.get(name)
    if not isinstance(value, dict):
        raise NatureProgressError(f"{name} must be an object")
    return value


def _required_string_list(args: dict[str, Any], name: str) -> list[str]:
    value = args.get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise NatureProgressError(f"{name} must be an array of non-empty strings")
    return value


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
        workflow_dir = _workflow(args)
        return command_memory_check(
            _root(args),
            workflow_dir,
            base=base,
            all_workflows=bool(args.get("all_workflows", False)) or workflow_dir is None,
            scope=args.get("scope", "shared"),
        )
    if name == "nature_memory_touch":
        return command_memory_touch(_root(args), _workflow(args), _required_string(args, "entry_id"), base=base)
    if name == "nature_memory_index":
        return command_memory_index(_root(args), _workflow(args), base=base, all_workflows=_workflow(args) is None)
    if name == "nature_memory_list":
        workflow_dir = _workflow(args)
        return command_memory_list(
            _root(args),
            workflow_dir,
            base=base,
            all_workflows=bool(args.get("all_workflows", False)) or workflow_dir is None,
            scope=args.get("scope", "shared"),
        )
    if name == "nature_memory_remember":
        return command_memory_remember(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string(args, "title"),
            _required_string(args, "body"),
            _required_object(args, "metadata"),
            entry_id=args.get("entry_id") or None,
            expected_etag=args.get("expected_etag") or None,
        )
    if name == "nature_memory_recall":
        project_root = _project_root_required(args)
        scope = _required_scope(args)
        query = _required_string(args, "query")
        if bool(args.get("all_workflows", False)):
            return command_memory_recall_all(
                project_root,
                _root(args),
                scope,
                query,
                top_k=args.get("top_k", 3),
                max_bytes=args.get("max_bytes", 4096),
                filters=args.get("filters") if isinstance(args.get("filters"), dict) else None,
            )
        return command_memory_recall(
            project_root,
            _required_string(args, "workflow_dir"),
            scope,
            query,
            top_k=args.get("top_k", 3),
            max_bytes=args.get("max_bytes", 4096),
            filters=args.get("filters") if isinstance(args.get("filters"), dict) else None,
        )
    if name == "nature_memory_show":
        return command_memory_show(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string(args, "entry_id"),
        )
    if name == "nature_memory_forget":
        return command_memory_forget(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string(args, "entry_id"),
            _required_string(args, "expected_etag"),
            _required_string(args, "reason"),
        )
    if name == "nature_memory_supersede":
        return command_memory_supersede(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string(args, "old_id"),
            _required_string(args, "expected_etag"),
            _required_string(args, "new_title"),
            _required_string(args, "new_body"),
            _required_object(args, "new_metadata"),
        )
    if name == "nature_memory_consolidate_plan":
        return command_memory_consolidate_plan(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string_list(args, "source_ids"),
        )
    if name == "nature_memory_consolidate_apply":
        source_etags = args.get("source_etags")
        if not isinstance(source_etags, (dict, list)):
            raise NatureProgressError("source_etags must be an object or array")
        return command_memory_consolidate_apply(
            _project_root_required(args),
            _required_string(args, "workflow_dir"),
            _required_scope(args),
            _required_string(args, "plan_id"),
            _required_string_list(args, "source_ids"),
            source_etags,
            _required_string(args, "new_title"),
            _required_string(args, "new_body"),
            _required_object(args, "new_metadata"),
        )
    if name == "nature_memory_migrate":
        all_workflows = bool(args.get("all_workflows", False))
        workflow_dir = _workflow(args)
        if not all_workflows and not workflow_dir:
            raise NatureProgressError("workflow_dir is required unless all_workflows is true")
        return command_memory_migrate(
            _project_root_required(args),
            workflow_dir,
            _required_scope(args),
            dry_run=bool(args.get("dry_run", False)),
            all_workflows=all_workflows,
        )
    if name == "nature_resume_with_memory":
        return resume_with_memory(
            _root(args),
            _workflow(args),
            project_root=_project_root_required(args),
            scope=_required_scope(args),
            query=args.get("query") if isinstance(args.get("query"), str) else None,
            top_k=args.get("top_k", 3),
            max_bytes=args.get("max_bytes", 4096),
        )
    if name == "nature_complete_with_memory_review":
        return complete_with_memory_review(
            _root(args),
            _required_string(args, "workflow_dir"),
            _required_string(args, "task_id"),
            _required_string(args, "evidence"),
            args.get("notes", "") if isinstance(args.get("notes", ""), str) else "",
            project_root=_project_root_required(args),
            scope=_required_scope(args),
            top_k=args.get("top_k", 3),
            max_bytes=args.get("max_bytes", 4096),
        )
    if name == "nature_block_with_memory_review":
        return block_with_memory_review(
            _root(args),
            _required_string(args, "workflow_dir"),
            _required_string(args, "task_id"),
            _required_string(args, "reason"),
            project_root=_project_root_required(args),
            scope=_required_scope(args),
            top_k=args.get("top_k", 3),
            max_bytes=args.get("max_bytes", 4096),
        )
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
                "serverInfo": {"name": "nature-workflow-progress", "version": SERVER_VERSION},
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
