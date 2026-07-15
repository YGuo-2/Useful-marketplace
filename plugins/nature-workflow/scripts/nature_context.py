#!/usr/bin/env python3
"""Application facade that composes Nature progress with bounded memory context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import nature_memory as memory
import nature_progress as progress


def _project_root(project_root: str | Path | None) -> Path:
    if project_root is None or not str(project_root).strip():
        raise memory.MemoryBoundaryError("project_root_not_found", "project_root must exist")
    try:
        root = Path(project_root).expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise memory.MemoryBoundaryError("project_root_not_found", "project_root must exist") from exc
    except OSError as exc:
        raise memory.MemoryBoundaryError(
            "project_root_unreadable",
            "project_root could not be resolved",
            retryable=True,
        ) from exc
    if not root.is_dir():
        raise memory.MemoryBoundaryError("invalid_project_root", "project_root must be a directory")
    return root


def _optional_string(value: Any, name: str, default: str | None = None) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str):
        raise progress.NatureProgressError(
            f"{name} must be a string when provided",
            code=f"invalid_{name}",
            context={"field": name},
        )
    return value


def _query_from_progress(summary: dict[str, Any], fallback: str = "nature workflow") -> str:
    parts: list[str] = []
    next_task = summary.get("next_task")
    if isinstance(next_task, dict):
        for key in ("id", "title", "blocker"):
            value = next_task.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    active_task = summary.get("active_task")
    if isinstance(active_task, str) and active_task.strip():
        parts.append(active_task.strip())
    return " ".join(parts) or fallback


def _memory_failure(error: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(error or {})
    payload.setdefault("code", "memory_review_unavailable")
    payload.setdefault("retryable", False)
    payload.setdefault("detail", "memory context could not be loaded; progress state remains authoritative")
    return {
        "status": "unavailable",
        "error": payload,
    }


def _exception_error(exc: Exception) -> dict[str, Any]:
    code = getattr(exc, "code", None) or "memory_review_internal_error"
    detail = getattr(exc, "detail", str(exc))
    # MemoryBoundaryError calls its base constructor after assigning its
    # fields, so recover the stable code/detail from its serialized message.
    if isinstance(exc, memory.MemoryBoundaryError) and code == "nature_progress_error":
        message = str(exc)
        if ": " in message:
            code, detail = message.split(": ", 1)
    return {
        "code": code,
        "detail": detail,
        "retryable": bool(getattr(exc, "retryable", False)),
        "exception_type": type(exc).__name__,
        **dict(getattr(exc, "context", {}) or {}),
    }


def _partial_parse_error(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "code": "memory_parse_errors",
        "detail": "memory context contains parse errors; valid entries were returned",
        "retryable": False,
        "diagnostics": diagnostics,
    }


def _bounded_payload(payload: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    def size(value: dict[str, Any]) -> int:
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    if size(payload) <= max_bytes:
        return payload
    bounded = dict(payload)
    bounded["diagnostics"] = list(payload.get("diagnostics", []))
    if isinstance(bounded.get("error"), dict):
        bounded["error"] = dict(bounded["error"])
        bounded["error"].pop("diagnostics", None)
    while size(bounded) > max_bytes and bounded["diagnostics"]:
        bounded["diagnostics"].pop()
    for key in ("results", "candidates"):
        while size(bounded) > max_bytes and bounded.get(key):
            bounded[key].pop()
    for key in ("file_etag", "query", "scope"):
        if size(bounded) <= max_bytes:
            break
        bounded.pop(key, None)
    if size(bounded) <= max_bytes:
        return bounded
    error = bounded.get("error") if isinstance(bounded.get("error"), dict) else {
        "code": "memory_context_budget",
        "detail": "memory context could not fit the requested byte budget",
        "retryable": False,
    }
    # At the minimum public budget, keep the stable error identity while
    # dropping verbose detail and nested diagnostics.
    minimal_error = {
        "code": str(error.get("code", "memory_context_budget")),
        "retryable": bool(error.get("retryable", False)),
    }
    minimal = {"status": bounded.get("status", "unavailable"), "error": minimal_error}
    if size(minimal) <= max_bytes:
        return minimal
    return {"status": "unavailable", "error": {"code": "memory_context_budget", "retryable": False}}


def _load_memory_context(
    root: Path,
    workflow_dir: str | Path,
    scope: str,
    query: str,
    *,
    top_k: int,
    max_bytes: int,
) -> dict[str, Any]:
    path = memory.resolve_memory_path(root, workflow_dir, scope)
    text, file_etag = memory._read_snapshot(path)
    document = memory.parse_memory_document(text, path)
    recall = memory.command_memory_recall(
        root,
        workflow_dir,
        scope,
        query,
        top_k=top_k,
        max_bytes=max_bytes,
        document=document,
        file_etag=file_etag,
    )
    if not recall.get("ok"):
        return _bounded_payload(_memory_failure(recall.get("error")), max_bytes)
    diagnostics = list(document.diagnostics)
    for item in recall.get("diagnostics", []):
        if item not in diagnostics:
            diagnostics.append(item)
    parse_errors = [item for item in diagnostics if item.get("severity") == memory.SEVERITY_ERROR]
    status = "partial" if parse_errors else "available"
    return _bounded_payload({
        "status": status,
        "query": query,
        "scope": scope,
        "file_etag": file_etag,
        "results": recall.get("results", []),
        "diagnostics": diagnostics,
        "error": _partial_parse_error(parse_errors) if parse_errors else None,
    }, max_bytes)


def resume_with_memory(
    workflow_root: str | None = None,
    workflow_dir: str | None = None,
    *,
    project_root: str | Path | None = None,
    scope: str = "shared",
    query: str | None = None,
    top_k: int = memory.RECALL_DEFAULT_TOP_K,
    max_bytes: int = memory.RECALL_MAX_BYTES,
) -> dict[str, Any]:
    root = _project_root(project_root)
    query = _optional_string(query, "query")
    progress_result = progress.command_resume(workflow_root, workflow_dir, base=root)
    derived_query = query or _query_from_progress(progress_result)
    try:
        context = _load_memory_context(
            root,
            progress_result["workflow_dir"],
            scope,
            derived_query,
            top_k=top_k,
            max_bytes=max_bytes,
        )
    except progress.NatureProgressError as exc:
        context = _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)
    except Exception as exc:
        context = _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)
    return {
        "ok": True,
        "action": "resume_with_memory",
        "progress": progress_result,
        "memory_context": context,
    }


def _review_after_progress(
    root: Path,
    progress_result: dict[str, Any],
    scope: str,
    query: str,
    *,
    top_k: int,
    max_bytes: int,
) -> dict[str, Any]:
    try:
        context = _load_memory_context(
            root,
            progress_result["workflow_dir"],
            scope,
            query,
            top_k=top_k,
            max_bytes=max_bytes,
        )
        return _bounded_payload({
            "status": context.get("status", "available"),
            "query": query,
            "candidates": context.get("results", []),
            "diagnostics": context.get("diagnostics", []),
            "error": context.get("error"),
        }, max_bytes)
    except progress.NatureProgressError as exc:
        return _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)
    except Exception as exc:
        return _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)


def complete_with_memory_review(
    workflow_root: str | None,
    workflow_dir: str | None,
    task_id: str,
    evidence: str,
    notes: str = "",
    *,
    project_root: str | Path | None = None,
    scope: str = "shared",
    top_k: int = memory.RECALL_DEFAULT_TOP_K,
    max_bytes: int = memory.RECALL_MAX_BYTES,
) -> dict[str, Any]:
    if workflow_dir is None or not str(workflow_dir).strip():
        raise progress.NatureProgressError("workflow_dir is required for mutation review")
    root = _project_root(project_root)
    notes = _optional_string(notes, "notes", "") or ""
    progress_result = progress.command_complete(
        workflow_root,
        workflow_dir,
        task_id,
        evidence,
        notes,
        base=root,
    )
    try:
        review = _review_after_progress(
            root,
            progress_result,
            scope,
            evidence.strip() or task_id,
            top_k=top_k,
            max_bytes=max_bytes,
        )
    except Exception as exc:
        review = _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)
    return {
        "ok": True,
        "action": "complete_with_memory_review",
        "progress_committed": True,
        "progress": progress_result,
        "memory_review": review,
    }


def block_with_memory_review(
    workflow_root: str | None,
    workflow_dir: str | None,
    task_id: str,
    reason: str,
    *,
    project_root: str | Path | None = None,
    scope: str = "shared",
    top_k: int = memory.RECALL_DEFAULT_TOP_K,
    max_bytes: int = memory.RECALL_MAX_BYTES,
) -> dict[str, Any]:
    if workflow_dir is None or not str(workflow_dir).strip():
        raise progress.NatureProgressError("workflow_dir is required for mutation review")
    root = _project_root(project_root)
    progress_result = progress.command_block(
        workflow_root,
        workflow_dir,
        task_id,
        reason,
        base=root,
    )
    try:
        review = _review_after_progress(
            root,
            progress_result,
            scope,
            reason.strip() or task_id,
            top_k=top_k,
            max_bytes=max_bytes,
        )
    except Exception as exc:
        review = _bounded_payload(_memory_failure(_exception_error(exc)), max_bytes)
    return {
        "ok": True,
        "action": "block_with_memory_review",
        "progress_committed": True,
        "progress": progress_result,
        "memory_review": review,
    }


__all__ = [
    "resume_with_memory",
    "complete_with_memory_review",
    "block_with_memory_review",
]
