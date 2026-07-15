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
        raise progress.NatureProgressError("project_root is required")
    return Path(project_root).expanduser().resolve(strict=True)


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
        return _memory_failure(recall.get("error"))
    status = "partial" if any(item.get("severity") == memory.SEVERITY_ERROR for item in document.diagnostics) else "available"
    return {
        "status": status,
        "query": query,
        "scope": scope,
        "file_etag": file_etag,
        "results": recall.get("results", []),
        "diagnostics": recall.get("diagnostics", []),
    }


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
        context = _memory_failure({"code": "memory_context_unavailable", "detail": str(exc), "retryable": False})
    except Exception:
        context = _memory_failure()
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
        return {
            "status": context.get("status", "available"),
            "query": query,
            "candidates": context.get("results", []),
            "diagnostics": context.get("diagnostics", []),
        }
    except progress.NatureProgressError as exc:
        return _memory_failure({"code": "memory_review_unavailable", "detail": str(exc), "retryable": False})
    except Exception:
        return _memory_failure()


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
    root = _project_root(project_root)
    progress_result = progress.command_complete(
        workflow_root,
        workflow_dir,
        task_id,
        evidence,
        notes,
        base=root,
    )
    review = _review_after_progress(
        root,
        progress_result,
        scope,
        evidence.strip() or task_id,
        top_k=top_k,
        max_bytes=max_bytes,
    )
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
    root = _project_root(project_root)
    progress_result = progress.command_block(
        workflow_root,
        workflow_dir,
        task_id,
        reason,
        base=root,
    )
    review = _review_after_progress(
        root,
        progress_result,
        scope,
        reason.strip() or task_id,
        top_k=top_k,
        max_bytes=max_bytes,
    )
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
