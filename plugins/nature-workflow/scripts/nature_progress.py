#!/usr/bin/env python3
"""Stdlib-only state engine for lightweight Nature workflows."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import nature_atomic


# When this file is executed as a script, nature_style imports
# ``nature_progress`` by module name. Reuse this module instance so both sides
# raise and catch the same NatureProgressError class.
if __name__ == "__main__":
    sys.modules["nature_progress"] = sys.modules[__name__]


DEFAULT_ROOT = "docs/nature-workflows"
SCHEMA_VERSION = 1
TASK_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,31}$")
SPEC_STATES = {"unset", "skipped", "ready"}
SPEC_SOURCES = {"template", "dictation"}
WORKFLOW_STATE_LOCK_FILE = ".nature-workflow-state.lock"
WORKFLOW_STATE_LOCK_TIMEOUT = 5.0


class WorkflowRecord(dict[str, Any]):
    """A JSON-compatible workflow record carrying its load-time snapshot ETag."""

    def __init__(self, *args: Any, snapshot_etag: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.snapshot_etag = snapshot_etag


@dataclass(frozen=True)
class _WorkflowFileSnapshot:
    raw: bytes
    etag: str
    exists: bool
    mode: int | None


_WORKFLOW_THREAD_LOCKS: dict[str, threading.Lock] = {}
_WORKFLOW_THREAD_LOCKS_GUARD = threading.Lock()
_WORKFLOW_LOCK_STATE = threading.local()


def default_spec() -> dict[str, Any]:
    """Format-spec gate state for one paper (see the optional Spec gate in SKILL.md)."""
    return {"status": "unset", "source": None, "path": None}


class NatureProgressError(Exception):
    """Raised for user-correctable workflow-state errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "nature_progress_error",
        retryable: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.detail = message
        self.retryable = retryable
        self.context = dict(context or {})
        super().__init__(message)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str | None, default: str = "nature-workflow") -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return (text or default)[:64].strip("-") or default


def clean_genre(value: str | None) -> str | None:
    """Normalize a paper-type genre to a slug, or None when unset.

    The allowed set (review/research/…) lives in the orchestrator's manifest,
    not here — this only normalizes case/spacing to match the
    ``paper_type/<genre>.md`` filename convention.
    """
    text = (value or "").strip()
    return slugify(text) if text else None


def base_dir() -> Path:
    return Path(os.environ.get("NATURE_WORKFLOW_BASE_DIR", os.getcwd())).resolve()


def _assert_within(path: Path, parent: Path, label: str) -> Path:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise NatureProgressError(f"{label} must stay within {parent}") from exc
    return path


def _checked_base(base: Path | None = None) -> Path:
    candidate = (base or base_dir()).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise NatureProgressError(
            "project root must exist",
            code="project_root_not_found",
            context={"project_root": str(candidate.resolve(strict=False))},
        ) from exc
    except OSError as exc:
        raise NatureProgressError(
            "project root could not be resolved",
            code="project_root_unreadable",
            retryable=True,
            context={"project_root": str(candidate.resolve(strict=False))},
        ) from exc
    if not resolved.is_dir():
        raise NatureProgressError(
            "project root must be a directory",
            code="invalid_project_root",
            context={"project_root": str(resolved)},
        )
    return resolved


def _root_error(
    code: str,
    detail: str,
    path: Path,
    *,
    label: str,
    retryable: bool = False,
) -> NatureProgressError:
    return NatureProgressError(
        detail,
        code=code,
        retryable=retryable,
        context={label: str(path)},
    )


def checked_root(
    root: str | None = None,
    *,
    base: Path | None = None,
    require_exists: bool = True,
) -> Path:
    base = _checked_base(base)
    raw = root or DEFAULT_ROOT
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    resolved = _assert_within(path.resolve(strict=False), base, "workflow root")
    if not require_exists:
        return resolved
    try:
        exists = resolved.exists()
        is_dir = resolved.is_dir() if exists else False
    except OSError as exc:
        raise _root_error(
            "workflow_root_unreadable",
            "workflow root could not be inspected",
            resolved,
            label="workflow_root",
            retryable=True,
        ) from exc
    if not exists:
        raise _root_error(
            "workflow_root_not_found",
            "workflow root must exist",
            resolved,
            label="workflow_root",
        )
    if not is_dir:
        raise _root_error(
            "workflow_root_not_directory",
            "workflow root must be a directory",
            resolved,
            label="workflow_root",
        )
    return resolved


def latest_workflow(root: Path) -> Path:
    try:
        if not root.exists():
            raise _root_error(
                "workflow_root_not_found",
                "workflow root must exist",
                root,
                label="workflow_root",
            )
        if not root.is_dir():
            raise _root_error(
                "workflow_root_not_directory",
                "workflow root must be a directory",
                root,
                label="workflow_root",
            )
        workflows = [p for p in root.iterdir() if p.is_dir() and (p / "nature.yml").exists()]
    except NatureProgressError:
        raise
    except OSError as exc:
        raise _root_error(
            "workflow_root_unreadable",
            "workflow root could not be inspected",
            root,
            label="workflow_root",
            retryable=True,
        ) from exc
    if not workflows:
        raise _root_error(
            "workflow_not_found",
            "no Nature workflows found under workflow root",
            root,
            label="workflow_root",
        )
    return sorted(workflows, key=lambda p: p.name)[-1]


def checked_workflow_dir(
    workflow: str | None = None,
    root: str | None = None,
    *,
    base: Path | None = None,
) -> Path:
    base = _checked_base(base)
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
    try:
        exists = resolved.exists()
        is_dir = resolved.is_dir() if exists else False
    except OSError as exc:
        raise _root_error(
            "workflow_dir_unreadable",
            "workflow directory could not be inspected",
            resolved,
            label="workflow_dir",
            retryable=True,
        ) from exc
    if not exists:
        raise _root_error(
            "workflow_dir_not_found",
            "workflow directory must exist",
            resolved,
            label="workflow_dir",
        )
    if not is_dir:
        raise _root_error(
            "workflow_dir_not_directory",
            "workflow directory must be a directory",
            resolved,
            label="workflow_dir",
        )
    return resolved


def make_task(task_id: str, title: str) -> dict[str, Any]:
    return {
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


def split_id_title(text: str) -> tuple[str | None, str]:
    """Parse a ``id: title`` (or ``id | title``) row into its parts.

    Returns ``(None, text)`` when the row carries no explicit id.
    """
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_.-]{0,31})\s*[:|]\s*(.+)$", text)
    if match:
        return match.group(1), match.group(2).strip()
    return None, text


def build_task(text: str, existing_ids: set[str]) -> dict[str, Any]:
    """Validate and build one task, giving an unlabeled row the first free ``T{n}``.

    Used for a mid-flow ``add-task`` where the id must not collide with any
    existing task in the record.
    """
    raw = (text or "").strip()
    if not raw:
        raise NatureProgressError("Task text is required")
    explicit_id, title = split_id_title(raw)
    task_id = explicit_id
    if task_id is None:
        n = 1
        while f"T{n}" in existing_ids:
            n += 1
        task_id = f"T{n}"
    if not TASK_ID_RE.match(task_id):
        raise NatureProgressError(f"Invalid task id: {task_id}")
    if task_id in existing_ids:
        raise NatureProgressError(f"Duplicate task id: {task_id}")
    if not title:
        raise NatureProgressError(f"Task {task_id} is missing a title")
    return make_task(task_id, title)


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
        explicit_id, title = split_id_title(text)
        task_id = explicit_id or f"T{index}"
        if not TASK_ID_RE.match(task_id):
            raise NatureProgressError(f"Invalid task id: {task_id}")
        if task_id in seen:
            raise NatureProgressError(f"Duplicate task id: {task_id}")
        if not title:
            raise NatureProgressError(f"Task {task_id} is missing a title")
        seen.add(task_id)
        tasks.append(make_task(task_id, title))
    if not tasks:
        raise NatureProgressError("At least one task is required")
    return tasks


def _workflow_state_etag(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _workflow_file_error(
    code: str,
    detail: str,
    path: Path,
    *,
    retryable: bool,
) -> NatureProgressError:
    return NatureProgressError(
        detail,
        code=code,
        retryable=retryable,
        context={"path": str(path)},
    )


def _read_workflow_file_snapshot(path: Path, *, state_file: bool) -> _WorkflowFileSnapshot:
    unsafe_code = "workflow_state_path_unsafe" if state_file else "workflow_mirror_path_unsafe"
    unreadable_code = "workflow_state_unreadable" if state_file else "workflow_mirror_unreadable"
    try:
        entry = os.lstat(path)
    except FileNotFoundError:
        return _WorkflowFileSnapshot(b"", _workflow_state_etag(b""), False, None)
    except OSError as exc:
        raise _workflow_file_error(
            unreadable_code,
            "workflow file could not be inspected",
            path,
            retryable=True,
        ) from exc
    if (
        stat.S_ISLNK(entry.st_mode)
        or not stat.S_ISREG(entry.st_mode)
        or getattr(entry, "st_nlink", 1) != 1
    ):
        raise _workflow_file_error(
            unsafe_code,
            "workflow files must be private regular files",
            path,
            retryable=False,
        )

    fd = -1
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            opened = os.fstat(handle.fileno())
            current = os.lstat(path)
            if (
                not stat.S_ISREG(opened.st_mode)
                or not stat.S_ISREG(current.st_mode)
                or getattr(opened, "st_nlink", 1) != 1
                or getattr(current, "st_nlink", 1) != 1
                or getattr(opened, "st_dev", None) != getattr(current, "st_dev", None)
                or getattr(opened, "st_ino", None) != getattr(current, "st_ino", None)
            ):
                raise _workflow_file_error(
                    unsafe_code,
                    "workflow file changed or became unsafe while it was read",
                    path,
                    retryable=False,
                )
            raw = handle.read()
    except NatureProgressError:
        raise
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise _workflow_file_error(
                unsafe_code,
                "workflow files must not be symbolic links",
                path,
                retryable=False,
            ) from exc
        raise _workflow_file_error(
            unreadable_code,
            "workflow file could not be read",
            path,
            retryable=True,
        ) from exc
    finally:
        if fd != -1:
            os.close(fd)

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _workflow_file_error(
            unreadable_code,
            "workflow files must be valid UTF-8",
            path,
            retryable=False,
        ) from exc
    return _WorkflowFileSnapshot(
        raw,
        _workflow_state_etag(raw),
        True,
        stat.S_IMODE(opened.st_mode),
    )


def _read_state_snapshot(state_path: Path) -> tuple[bytes, str]:
    snapshot = _read_workflow_file_snapshot(state_path, state_file=True)
    return snapshot.raw, snapshot.etag


def _workflow_thread_lock(lock_path: Path) -> threading.Lock:
    key = _workflow_lock_key(lock_path)
    with _WORKFLOW_THREAD_LOCKS_GUARD:
        return _WORKFLOW_THREAD_LOCKS.setdefault(key, threading.Lock())


def _workflow_lock_key(lock_path: Path) -> str:
    return os.path.normcase(str(lock_path.resolve(strict=False)))


def _held_workflow_locks() -> set[str]:
    held = getattr(_WORKFLOW_LOCK_STATE, "held", None)
    if held is None:
        held = set()
        _WORKFLOW_LOCK_STATE.held = held
    return held


def _state_lock_error(
    code: str,
    detail: str,
    workflow_dir: Path,
    lock_path: Path,
    *,
    retryable: bool = True,
    timeout: float | None = None,
) -> NatureProgressError:
    context: dict[str, Any] = {
        "workflow_dir": str(workflow_dir),
        "lock_path": str(lock_path),
    }
    if timeout is not None:
        context["timeout_seconds"] = max(0.0, timeout)
    return NatureProgressError(detail, code=code, retryable=retryable, context=context)


def _lock_is_busy(exc: OSError) -> bool:
    return exc.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK} or getattr(
        exc, "winerror", None
    ) in {32, 33}


def _check_state_lock_path(lock_path: Path, workflow_dir: Path) -> None:
    try:
        info = os.lstat(lock_path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise _state_lock_error(
            "workflow_state_lock_unavailable",
            "workflow state lock could not be inspected",
            workflow_dir,
            lock_path,
        ) from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or getattr(info, "st_nlink", 1) != 1:
        raise _state_lock_error(
            "workflow_state_lock_unsafe",
            "workflow state lock must be a private regular file",
            workflow_dir,
            lock_path,
            retryable=False,
        )


def _assert_open_lock_identity(handle: Any, lock_path: Path, workflow_dir: Path) -> None:
    try:
        opened = os.fstat(handle.fileno())
        current = os.stat(lock_path, follow_symlinks=False)
    except OSError as exc:
        raise _state_lock_error(
            "workflow_state_lock_unavailable",
            "workflow state lock could not be inspected while held",
            workflow_dir,
            lock_path,
        ) from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or getattr(opened, "st_nlink", 1) != 1
        or getattr(current, "st_nlink", 1) != 1
        or getattr(opened, "st_dev", None) != getattr(current, "st_dev", None)
        or getattr(opened, "st_ino", None) != getattr(current, "st_ino", None)
    ):
        raise _state_lock_error(
            "workflow_state_lock_replaced",
            "workflow state lock was replaced while it was held",
            workflow_dir,
            lock_path,
            retryable=False,
        )


@contextmanager
def workflow_state_lock(
    workflow_dir: str | Path,
    timeout: float = WORKFLOW_STATE_LOCK_TIMEOUT,
):
    """Serialize workflow state writes across threads and processes."""
    workflow = Path(workflow_dir).expanduser().resolve(strict=False)
    if not workflow.is_dir():
        raise NatureProgressError(
            "workflow directory must exist before locking state",
            code="invalid_workflow_dir",
            context={"workflow_dir": str(workflow)},
        )
    lock_path = workflow / WORKFLOW_STATE_LOCK_FILE
    try:
        timeout = float(timeout)
    except (TypeError, ValueError) as exc:
        raise _state_lock_error(
            "workflow_state_lock_timeout_invalid",
            "workflow state lock timeout must be a finite number",
            workflow,
            lock_path,
            retryable=False,
        ) from exc
    if not math.isfinite(timeout) or timeout > threading.TIMEOUT_MAX:
        raise _state_lock_error(
            "workflow_state_lock_timeout_invalid",
            "workflow state lock timeout must be a finite, platform-supported number",
            workflow,
            lock_path,
            retryable=False,
        )
    timeout = max(0.0, timeout)
    deadline = time.monotonic() + timeout
    local_lock = _workflow_thread_lock(lock_path)
    if not local_lock.acquire(timeout=timeout):
        raise _state_lock_error(
            "workflow_state_lock_timeout",
            "workflow state lock timed out; retry with bounded backoff",
            workflow,
            lock_path,
            timeout=timeout,
        )

    handle = None
    acquired = False
    try:
        _check_state_lock_path(lock_path, workflow)
        try:
            flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            handle = os.fdopen(os.open(lock_path, flags, 0o600), "r+b")
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise _state_lock_error(
                    "workflow_state_lock_unsafe",
                    "workflow state lock must not be a symbolic link",
                    workflow,
                    lock_path,
                    retryable=False,
                ) from exc
            raise _state_lock_error(
                "workflow_state_lock_unavailable",
                "workflow state lock could not be opened",
                workflow,
                lock_path,
            ) from exc

        _assert_open_lock_identity(handle, lock_path, workflow)

        remaining = max(0.0, deadline - time.monotonic())
        if os.name == "nt":
            import msvcrt

            try:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
            except OSError as exc:
                raise _state_lock_error(
                    "workflow_state_lock_unavailable",
                    "workflow state lock could not be initialized",
                    workflow,
                    lock_path,
                ) from exc
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError as exc:
                    if not _lock_is_busy(exc):
                        raise _state_lock_error(
                            "workflow_state_lock_unavailable",
                            "workflow state lock backend failed",
                            workflow,
                            lock_path,
                        ) from exc
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(min(0.025, remaining))
                    remaining = max(0.0, deadline - time.monotonic())
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError as exc:
                    if not _lock_is_busy(exc):
                        raise _state_lock_error(
                            "workflow_state_lock_unavailable",
                            "workflow state lock backend failed",
                            workflow,
                            lock_path,
                        ) from exc
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(min(0.025, remaining))
                    remaining = max(0.0, deadline - time.monotonic())
        if not acquired:
            raise _state_lock_error(
                "workflow_state_lock_timeout",
                "workflow state lock timed out; retry with bounded backoff",
                workflow,
                lock_path,
                timeout=timeout,
            )
        lock_key = _workflow_lock_key(lock_path)
        held_locks = _held_workflow_locks()
        held_locks.add(lock_key)
        try:
            yield lock_path
            _assert_open_lock_identity(handle, lock_path, workflow)
        finally:
            held_locks.discard(lock_key)
    finally:
        if acquired and handle is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        if handle is not None:
            handle.close()
        local_lock.release()


def load_record(workflow_dir: Path) -> WorkflowRecord:
    state_path = workflow_dir / "nature.yml"
    snapshot = _read_workflow_file_snapshot(state_path, state_file=True)
    if not snapshot.exists:
        raise NatureProgressError(f"Missing nature.yml in {workflow_dir}")
    try:
        data = json.loads(snapshot.raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise NatureProgressError("nature.yml must be valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise NatureProgressError(f"Invalid nature.yml JSON/YAML-compatible state: {exc}") from exc
    if not isinstance(data, dict):
        raise NatureProgressError("nature.yml must contain an object")
    return WorkflowRecord(data, snapshot_etag=snapshot.etag)


def _next_record_updated_at(previous: Any) -> str:
    candidate = datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(previous, str):
        try:
            parsed = datetime.fromisoformat(previous.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc).replace(microsecond=0)
            if parsed >= candidate:
                candidate = parsed + timedelta(seconds=1)
        except (OverflowError, ValueError):
            pass
    return candidate.isoformat().replace("+00:00", "Z")


def _prefixed_file_etag(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _conditional_replace_workflow_text(
    path: Path,
    text: str,
    *,
    expected_etag: str,
    file_mode: int | None,
    state_file: bool,
) -> None:
    try:
        nature_atomic.atomic_replace_text(
            path,
            text,
            expected_etag=expected_etag.removeprefix("sha256:"),
            mutation_context={"workflow_path": str(path)},
            file_mode=file_mode,
        )
    except nature_atomic.AtomicReplaceError as exc:
        conflict = exc.code == "file_changed_outside_lock"
        if state_file and conflict:
            code = "workflow_state_conflict"
            detail = "workflow state changed after it was loaded; reload and retry"
        elif conflict:
            code = "workflow_mirror_conflict"
            detail = "workflow mirror changed during state commit; reload and retry"
        else:
            code = "workflow_state_write_failed" if state_file else "workflow_mirror_write_failed"
            detail = "workflow state could not be committed atomically"
        context = {
            "path": str(path),
            "expected_etag": expected_etag,
            "cause_code": exc.code,
            **dict(exc.context),
        }
        actual = _prefixed_file_etag(exc.context.get("current_file_etag"))
        if actual is not None:
            context["actual_etag"] = actual
        raise NatureProgressError(
            detail,
            code=code,
            retryable=conflict or exc.retryable,
            context=context,
        ) from exc
    except OSError as exc:
        raise NatureProgressError(
            "workflow state could not be committed atomically",
            code="workflow_state_write_failed" if state_file else "workflow_mirror_write_failed",
            retryable=True,
            context={"path": str(path), "expected_etag": expected_etag},
        ) from exc


def _conditional_remove_workflow_file(path: Path, *, expected_etag: str) -> None:
    current = _read_workflow_file_snapshot(path, state_file=False)
    if not current.exists:
        return
    if current.etag != expected_etag:
        raise NatureProgressError(
            "workflow mirror changed before rollback; external content was preserved",
            code="workflow_mirror_conflict",
            retryable=True,
            context={
                "path": str(path),
                "expected_etag": expected_etag,
                "actual_etag": current.etag,
            },
        )

    fd, recovery_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".rollback",
    )
    os.close(fd)
    os.unlink(recovery_name)
    recovery_path = Path(recovery_name)
    try:
        os.replace(path, recovery_path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise NatureProgressError(
            "new workflow mirror could not be removed during rollback",
            code="workflow_state_rollback_failed",
            retryable=True,
            context={"path": str(path)},
        ) from exc

    moved = _read_workflow_file_snapshot(recovery_path, state_file=False)
    if moved.etag != expected_etag:
        if not path.exists():
            try:
                os.replace(recovery_path, path)
            except OSError as exc:
                raise NatureProgressError(
                    "externally changed mirror could not be restored after rollback conflict",
                    code="workflow_state_rollback_failed",
                    retryable=True,
                    context={"path": str(path), "recovery_path": str(recovery_path)},
                ) from exc
        raise NatureProgressError(
            "workflow mirror changed during rollback; external content was preserved",
            code="workflow_mirror_conflict",
            retryable=True,
            context={"path": str(path)},
        )
    recovery_path.unlink()


def _rollback_workflow_mirrors(
    applied: list[tuple[Path, _WorkflowFileSnapshot, str]],
    *,
    cause: BaseException,
) -> None:
    failures: list[dict[str, Any]] = []
    for path, original, written_etag in reversed(applied):
        try:
            if original.exists:
                _conditional_replace_workflow_text(
                    path,
                    original.raw.decode("utf-8"),
                    expected_etag=written_etag,
                    file_mode=original.mode,
                    state_file=False,
                )
            else:
                _conditional_remove_workflow_file(path, expected_etag=written_etag)
        except NatureProgressError as exc:
            failures.append({"path": str(path), "code": exc.code})
    if failures:
        raise NatureProgressError(
            "workflow state commit failed and one or more mirror files could not be restored",
            code="workflow_state_rollback_failed",
            retryable=True,
            context={"failures": failures},
        ) from cause


def _save_record_locked(workflow_dir: Path, record: dict[str, Any]) -> None:
    state_path = workflow_dir / "nature.yml"
    progress_path = workflow_dir / "progress.md"
    tasks_path = workflow_dir / "tasks.md"
    snapshots = {
        state_path: _read_workflow_file_snapshot(state_path, state_file=True),
        progress_path: _read_workflow_file_snapshot(progress_path, state_file=False),
        tasks_path: _read_workflow_file_snapshot(tasks_path, state_file=False),
    }
    state_snapshot = snapshots[state_path]

    if isinstance(record, WorkflowRecord):
        expected_etag = record.snapshot_etag
        if expected_etag is None:
            raise NatureProgressError(
                "workflow records without a load-time snapshot cannot overwrite state",
                code="workflow_state_snapshot_required",
                retryable=False,
                context={"state_path": str(state_path)},
            )
    elif state_snapshot.exists:
        raise NatureProgressError(
            "load the workflow record before saving existing state",
            code="workflow_state_snapshot_required",
            retryable=False,
            context={"state_path": str(state_path)},
        )
    else:
        expected_etag = _workflow_state_etag(b"")

    if state_snapshot.etag != expected_etag:
        raise NatureProgressError(
            "workflow state changed after it was loaded; reload and retry",
            code="workflow_state_conflict",
            retryable=True,
            context={
                "workflow_dir": str(workflow_dir),
                "state_path": str(state_path),
                "expected_etag": expected_etag,
                "actual_etag": state_snapshot.etag,
            },
        )

    had_updated_at = "updated_at" in record
    original_updated_at = record.get("updated_at")
    committed = False
    applied: list[tuple[Path, _WorkflowFileSnapshot, str]] = []
    try:
        record["updated_at"] = _next_record_updated_at(original_updated_at)
        state_text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        rendered = {
            progress_path: render_progress(record),
            tasks_path: render_tasks(record),
        }
        state_bytes = state_text.encode("utf-8")

        for path in (progress_path, tasks_path):
            text = rendered[path]
            original = snapshots[path]
            written_etag = _workflow_state_etag(text.encode("utf-8"))
            if written_etag == original.etag:
                continue
            _conditional_replace_workflow_text(
                path,
                text,
                expected_etag=original.etag,
                file_mode=original.mode,
                state_file=False,
            )
            applied.append((path, original, written_etag))

        expected_mirror_etags = {
            path: next(
                (written_etag for applied_path, _, written_etag in applied if applied_path == path),
                snapshots[path].etag,
            )
            for path in (progress_path, tasks_path)
        }
        for path, expected_mirror_etag in expected_mirror_etags.items():
            current = _read_workflow_file_snapshot(path, state_file=False)
            if current.etag != expected_mirror_etag:
                raise NatureProgressError(
                    "workflow mirror changed before the state commit; reload and retry",
                    code="workflow_mirror_conflict",
                    retryable=True,
                    context={
                        "path": str(path),
                        "expected_etag": expected_mirror_etag,
                        "actual_etag": current.etag,
                    },
                )

        _conditional_replace_workflow_text(
            state_path,
            state_text,
            expected_etag=state_snapshot.etag,
            file_mode=state_snapshot.mode,
            state_file=True,
        )
        committed = True
        if isinstance(record, WorkflowRecord):
            record.snapshot_etag = _workflow_state_etag(state_bytes)
    except BaseException as exc:
        _rollback_workflow_mirrors(applied, cause=exc)
        raise
    finally:
        if not committed:
            if had_updated_at:
                record["updated_at"] = original_updated_at
            else:
                record.pop("updated_at", None)


def save_record(
    workflow_dir: Path,
    record: dict[str, Any],
    *,
    already_locked: bool = False,
    lock_timeout: float = WORKFLOW_STATE_LOCK_TIMEOUT,
) -> None:
    workflow_dir.mkdir(parents=True, exist_ok=True)
    if already_locked:
        lock_key = _workflow_lock_key(workflow_dir / WORKFLOW_STATE_LOCK_FILE)
        if lock_key not in _held_workflow_locks():
            raise NatureProgressError(
                "already_locked requires the current thread to hold the workflow state lock",
                code="workflow_state_lock_required",
                context={
                    "workflow_dir": str(workflow_dir),
                    "lock_path": str(workflow_dir / WORKFLOW_STATE_LOCK_FILE),
                },
            )
        _save_record_locked(workflow_dir, record)
        return
    with workflow_state_lock(workflow_dir, timeout=lock_timeout):
        _save_record_locked(workflow_dir, record)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name: str | None = None
    try:
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
        tmp_name = None
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def find_task(record: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in record.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise NatureProgressError(f"Unknown task id: {task_id}")


def assert_no_other_active(record: dict[str, Any], task_id: str) -> None:
    """Reject starting/blocking ``task_id`` while a different task is active.

    Only an in-progress (``active``) task counts as occupying the workflow. A
    ``blocked`` task does not, so the user may switch to another task while one
    is parked on a blocker.
    """
    active = next(
        (item for item in record.get("tasks", []) if item.get("status") == "active"),
        None,
    )
    if active and active.get("id") != task_id:
        raise NatureProgressError(f"Task {active.get('id')} is already active")


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
    """Recompute ``status``/``active_task`` purely from task statuses.

    This is the single source of truth for workflow-level state and must be
    called at the end of every write command (and may be called by read
    commands). Because it is deterministic, a read command that recomputes in
    memory yields the same values already persisted on disk, so reads never
    drift from the saved ``nature.yml``.

    Priority: an in-progress (``active``) task wins and drives ``active_task``
    with workflow ``status="open"``; otherwise a ``blocked`` task surfaces with
    ``status="blocked"``; all-completed is ``completed``; everything else is an
    idle ``open`` workflow with no active task.
    """
    tasks = record.get("tasks", [])
    if tasks and all(task.get("status") == "completed" for task in tasks):
        record["status"] = "completed"
        record["active_task"] = None
        return
    active = next((task for task in tasks if task.get("status") == "active"), None)
    if active is not None:
        record["status"] = "open"
        record["active_task"] = active.get("id")
        return
    blocked = next((task for task in tasks if task.get("status") == "blocked"), None)
    if blocked is not None:
        record["status"] = "blocked"
        record["active_task"] = blocked.get("id")
        return
    record["status"] = "open"
    record["active_task"] = None


def summarize(record: dict[str, Any], workflow_dir: Path) -> dict[str, Any]:
    tasks = record.get("tasks", [])
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.get("status", "unknown")] = counts.get(task.get("status", "unknown"), 0) + 1
    # next_task is the actionable step, and follows active_task's priority so a
    # read never contradicts itself: the in-progress task first (even when a
    # lower-index task is still pending), then the first pending step, and only a
    # blocked task when nothing else is left — it is parked (workflow.md §2.5).
    next_task = (
        next((task for task in tasks if task.get("status") == "active"), None)
        or next((task for task in tasks if task.get("status") == "pending"), None)
        or next((task for task in tasks if task.get("status") == "blocked"), None)
    )
    summary = {
        "workflow_dir": str(workflow_dir),
        "title": record.get("title", ""),
        "slug": record.get("slug", ""),
        "status": record.get("status", "unknown"),
        "active_task": record.get("active_task"),
        "genre": record.get("genre"),
        "spec": record.get("spec") or default_spec(),
        "task_counts": counts,
        "next_task": next_task,
        "files": {
            "nature": str(workflow_dir / "nature.yml"),
            "progress": str(workflow_dir / "progress.md"),
            "tasks": str(workflow_dir / "tasks.md"),
        },
    }
    if "prose_style" in record:
        from nature_style import style_summary

        summary["prose_style"] = style_summary(record)
    return summary


def render_progress(record: dict[str, Any]) -> str:
    active = record.get("active_task") or "none"
    spec = record.get("spec") or default_spec()
    spec_line = spec.get("status", "unset")
    if spec.get("source"):
        spec_line += f" ({spec.get('source')})"
    lines = [
        "# Nature Workflow Progress",
        "",
        f"- Title: {record.get('title', '')}",
        f"- Slug: {record.get('slug', '')}",
        f"- Genre: {record.get('genre') or 'unset'}",
        f"- Status: {record.get('status', '')}",
        f"- Active task: {active}",
        f"- Spec: {spec_line}",
        f"- Created: {record.get('created_at', '')}",
        f"- Updated: {record.get('updated_at', '')}",
        "",
        "## Tasks",
        "",
    ]
    if "prose_style" in record:
        from nature_style import style_summary

        prose_style = style_summary(record) or {}
        selection = prose_style.get("selection_status", "none")
        selected = prose_style.get("selected_profile_id") or "none"
        lines[8:8] = [f"- Prose style: {selection} ({selected})"]
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
    genre: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    root = checked_root(workflow_root, base=base, require_exists=False)
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
        "genre": clean_genre(genre),
        "status": "open",
        "active_task": None,
        "spec": default_spec(),
        "tasks": parse_tasks(tasks),
        "log": [],
    }
    append_log(record, "new", "Workflow created")
    save_record(workflow_dir, record)
    return {"ok": True, "action": "new", **summarize(record, workflow_dir)}


def command_discover(workflow_root: str | None = None, *, base: Path | None = None) -> dict[str, Any]:
    root = checked_root(workflow_root, base=base)
    workflows: list[dict[str, Any]] = []
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
    assert_no_other_active(record, task_id)
    task["status"] = "active"
    task["started_at"] = task.get("started_at") or now_utc()
    task["blocked_at"] = None
    task["blocker"] = ""
    append_log(record, "start", "Task started", task_id)
    update_workflow_status(record)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "start", **summarize(record, workflow_dir)}


def command_complete(
    workflow_root: str | None,
    workflow: str | None,
    task_id: str,
    evidence: str,
    notes: str = "",
    style_receipt: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    if not evidence.strip():
        raise NatureProgressError("Completion evidence is required")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    project_root = _checked_base(base)
    with workflow_state_lock(workflow_dir):
        record = load_record(workflow_dir)
        task = find_task(record, task_id)
        original_record = json.loads(json.dumps(record, ensure_ascii=False))
        style_guard = None
        if "prose_style" in record:
            from nature_style import assert_style_completion_allowed

            style_guard = assert_style_completion_allowed
            style_guard(
                project_root,
                workflow_dir,
                record,
                task,
                evidence,
                style_receipt,
            )
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
        if style_guard is not None:
            style_guard(
                project_root,
                workflow_dir,
                record,
                task,
                evidence,
                style_receipt,
            )
        save_record(workflow_dir, record, already_locked=True)
        if style_guard is not None:
            try:
                style_guard(
                    project_root,
                    workflow_dir,
                    record,
                    task,
                    evidence,
                    style_receipt,
                )
            except BaseException as exc:
                try:
                    record.clear()
                    record.update(original_record)
                    save_record(workflow_dir, record, already_locked=True)
                except BaseException as rollback_exc:
                    raise NatureProgressError(
                        "completion evidence changed and task state could not be rolled back",
                        code="workflow_completion_rollback_failed",
                        retryable=True,
                        context={"workflow_dir": str(workflow_dir), "task_id": task_id},
                    ) from rollback_exc
                raise
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
    assert_no_other_active(record, task_id)
    task["status"] = "blocked"
    task["blocked_at"] = now_utc()
    task["blocker"] = reason.strip()
    append_log(record, "block", reason.strip(), task_id)
    update_workflow_status(record)
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


def command_spec(
    workflow_root: str | None,
    workflow: str | None,
    status: str,
    source: str | None = None,
    path: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    """Record the optional format-spec gate decision for a paper workflow.

    ``status`` moves between ``unset`` (never asked), ``skipped`` (user declined,
    so downstream skills stop re-prompting), and ``ready`` (a ``spec.md`` exists
    and is the format contract). This only tracks the decision; the spec.md file
    itself is authored by the agent per the two branches described in SKILL.md.
    """
    if status not in SPEC_STATES:
        raise NatureProgressError(f"Invalid spec status: {status}")
    if source is not None and source not in SPEC_SOURCES:
        raise NatureProgressError(f"Invalid spec source: {source}")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    spec = record.get("spec")
    if not isinstance(spec, dict):
        spec = default_spec()
    spec["status"] = status
    if status == "ready":
        spec["source"] = source or spec.get("source")
        spec["path"] = path or spec.get("path") or "spec.md"
    elif status == "skipped":
        spec["source"] = None
        spec["path"] = None
    else:  # unset
        spec["source"] = source
        spec["path"] = None
    record["spec"] = spec
    detail = f"spec {status}" + (f" ({spec['source']})" if spec.get("source") else "")
    append_log(record, "spec", detail)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "spec", **summarize(record, workflow_dir)}


def command_genre(
    workflow_root: str | None,
    workflow: str | None,
    genre: str,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    """Persist the top-level paper-type genre for a workflow (mirrors ``spec``).

    Genre is normally known at ``new`` and set there; this command lets the
    orchestrator correct it mid-flow. Values are free-form slugs — the allowed
    set lives in the orchestrator manifest, not the engine.
    """
    value = clean_genre(genre)
    if value is None:
        raise NatureProgressError("Genre value is required")
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    record["genre"] = value
    append_log(record, "genre", f"genre {value}")
    save_record(workflow_dir, record)
    return {"ok": True, "action": "genre", **summarize(record, workflow_dir)}


def command_add_task(
    workflow_root: str | None,
    workflow: str | None,
    text: str,
    after: str | None = None,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    """Insert one task into an existing workflow (append, or after ``after``).

    Adding a pending task to an all-completed workflow reopens it, since
    ``update_workflow_status`` no longer sees every task as completed.
    """
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    tasks = record.setdefault("tasks", [])
    existing_ids = {task.get("id") for task in tasks}
    task = build_task(text, existing_ids)
    if after:
        find_task(record, after)  # validates existence
        index = next(i for i, item in enumerate(tasks) if item.get("id") == after) + 1
        tasks.insert(index, task)
    else:
        tasks.append(task)
    append_log(record, "add-task", task["title"], task["id"])
    update_workflow_status(record)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "add-task", **summarize(record, workflow_dir)}


def command_remove_task(
    workflow_root: str | None,
    workflow: str | None,
    task_id: str,
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    """Drop a pending or blocked task from a workflow.

    An ``active`` task is refused to protect the single-active invariant, and a
    ``completed`` task to protect its recorded evidence history.
    """
    workflow_dir = checked_workflow_dir(workflow, workflow_root, base=base)
    record = load_record(workflow_dir)
    task = find_task(record, task_id)  # validates existence
    if task.get("status") in ("active", "completed"):
        raise NatureProgressError(f"Cannot remove {task.get('status')} task {task_id}")
    # ponytail: allow removing the last task — an empty workflow is a harmless
    # open/idle record; add a "keep at least one" guard only if a need appears.
    record["tasks"] = [item for item in record.get("tasks", []) if item.get("id") != task_id]
    append_log(record, "remove-task", "Task removed", task_id)
    update_workflow_status(record)
    save_record(workflow_dir, record)
    return {"ok": True, "action": "remove-task", **summarize(record, workflow_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage lightweight Nature workflow state.")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create a new workflow directory.")
    new.add_argument("--root", default=DEFAULT_ROOT)
    new.add_argument("--slug", default="nature-workflow")
    new.add_argument("--title", default="")
    new.add_argument("--task", action="append", default=[])
    new.add_argument("--genre", default="")

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
    complete.add_argument("--style-receipt", default="")
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

    spec = sub.add_parser("spec", help="Record the optional format-spec gate decision.")
    spec.add_argument("--status", required=True, choices=sorted(SPEC_STATES))
    spec.add_argument("--source", default="", choices=["", *sorted(SPEC_SOURCES)])
    spec.add_argument("--path", default="")
    spec.add_argument("--root", default=DEFAULT_ROOT)
    spec.add_argument("--workflow", default="")

    genre = sub.add_parser("genre", help="Set the paper-type genre for a workflow.")
    genre.add_argument("value")
    genre.add_argument("--root", default=DEFAULT_ROOT)
    genre.add_argument("--workflow", default="")

    add_task = sub.add_parser("add-task", help="Insert a task into an existing workflow.")
    add_task.add_argument("text", help='"id: title" (or plain title to auto-number).')
    add_task.add_argument("--after", default="", help="Insert after this task id.")
    add_task.add_argument("--root", default=DEFAULT_ROOT)
    add_task.add_argument("--workflow", default="")

    remove_task = sub.add_parser("remove-task", help="Remove a pending/blocked task.")
    remove_task.add_argument("task_id")
    remove_task.add_argument("--root", default=DEFAULT_ROOT)
    remove_task.add_argument("--workflow", default="")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "new":
        return command_new_workflow(args.root, args.slug, args.title, args.task, args.genre or None)
    if args.command == "discover":
        return command_discover(args.root)
    if args.command == "status":
        return command_status(args.root, args.workflow or None)
    if args.command == "resume":
        return command_resume(args.root, args.workflow or None)
    if args.command == "start":
        return command_start(args.root, args.workflow or None, args.task_id)
    if args.command == "complete":
        return command_complete(
            args.root,
            args.workflow or None,
            args.task_id,
            args.evidence,
            args.notes,
            args.style_receipt or None,
        )
    if args.command == "block":
        return command_block(args.root, args.workflow or None, args.task_id, args.reason)
    if args.command == "log":
        return command_log_note(args.root, args.workflow or None, args.note, args.task_id or None)
    if args.command == "spec":
        return command_spec(
            args.root,
            args.workflow or None,
            args.status,
            args.source or None,
            args.path or None,
        )
    if args.command == "genre":
        return command_genre(args.root, args.workflow or None, args.value)
    if args.command == "add-task":
        return command_add_task(args.root, args.workflow or None, args.text, args.after or None)
    if args.command == "remove-task":
        return command_remove_task(args.root, args.workflow or None, args.task_id)
    raise NatureProgressError(f"Unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        result = dispatch(parser.parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except NatureProgressError as exc:
        error = {
            "code": exc.code,
            "detail": exc.detail,
            "retryable": exc.retryable,
            **exc.context,
        }
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
