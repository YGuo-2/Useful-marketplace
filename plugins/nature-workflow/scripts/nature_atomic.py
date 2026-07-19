#!/usr/bin/env python3
"""Low-level compare-and-swap text replacement for Nature workflow files."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


EMPTY_ETAG = hashlib.sha256(b"").hexdigest()
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2
_RENAME_SWAP = 2
_RENAME_EXCL = 4
_WINDOWS_ALREADY_EXISTS = {80, 183}
_WINDOWS_NOT_FOUND = {2, 3}


class AtomicReplaceError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        *,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.retryable = retryable
        self.context = dict(context or {})
        super().__init__(detail)


def file_etag(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _error_context(path: Path, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    context = {"path": str(path)}
    if extra:
        context.update(extra)
    return context


def _read_snapshot(path: Path) -> tuple[bytes, str]:
    try:
        entry = os.lstat(path)
    except FileNotFoundError:
        return b"", EMPTY_ETAG
    except OSError as exc:
        raise AtomicReplaceError(
            "path_unreadable",
            "file could not be inspected",
            retryable=True,
            context=_error_context(path),
        ) from exc
    if (
        stat.S_ISLNK(entry.st_mode)
        or not stat.S_ISREG(entry.st_mode)
        or getattr(entry, "st_nlink", 1) != 1
    ):
        raise AtomicReplaceError(
            "path_unsafe",
            "file must be a private regular file",
            context=_error_context(path),
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
                raise AtomicReplaceError(
                    "file_changed_outside_lock",
                    "file changed while its snapshot was read",
                    retryable=True,
                    context=_error_context(path),
                )
            raw = handle.read()
    except AtomicReplaceError:
        raise
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            code = "path_unsafe"
            detail = "file must not be a symbolic link"
            retryable = False
        else:
            code = "path_unreadable"
            detail = "file could not be read"
            retryable = True
        raise AtomicReplaceError(
            code,
            detail,
            retryable=retryable,
            context=_error_context(path),
        ) from exc
    finally:
        if fd != -1:
            os.close(fd)
    return raw, file_etag(raw)


def _entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    return True


def _best_effort_unlink(path: str | Path) -> bool:
    """Remove an internal artifact without changing a completed CAS result."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _artifact_path(path: Path, role: str) -> Path:
    """Return an unpredictable, same-directory path for a CAS recovery file."""
    for _ in range(32):
        candidate = path.parent / f".{path.name}.{role}.{uuid.uuid4().hex}"
        if not _entry_exists(candidate):
            return candidate
    raise AtomicReplaceError(
        "cas_unavailable",
        "a private recovery path could not be allocated",
        retryable=True,
        context=_error_context(path),
    )


def _conflict(
    path: Path,
    expected_etag: str,
    current_etag: str,
    context: dict[str, Any] | None,
    detail: str,
    **extra: Any,
) -> AtomicReplaceError:
    return AtomicReplaceError(
        "file_changed_outside_lock",
        detail,
        retryable=True,
        context=_error_context(
            path,
            {
                "current_file_etag": current_etag,
                "expected_file_etag": expected_etag,
                **extra,
                **(context or {}),
            },
        ),
    )


def atomic_replace_text(
    path: Path,
    text: str,
    *,
    expected_etag: str,
    mutation_context: dict[str, Any] | None = None,
    file_mode: int | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(text.encode("utf-8"))
            temporary.flush()
            os.fsync(temporary.fileno())
        if file_mode is not None:
            try:
                os.chmod(temporary_name, stat.S_IMODE(file_mode))
            except OSError as exc:
                raise AtomicReplaceError(
                    "temporary_mode_failed",
                    "replacement file mode could not be preserved",
                    retryable=True,
                    context=_error_context(path, mutation_context),
                ) from exc

        _, current_etag = _read_snapshot(path)
        if current_etag != expected_etag:
            raise _conflict(
                path,
                expected_etag,
                current_etag,
                mutation_context,
                "file changed before atomic replacement",
            )

        try:
            if os.name == "nt":
                temporary_name = _replace_windows(
                    temporary_name,
                    path,
                    expected_etag,
                    mutation_context,
                )
            else:
                temporary_name = _replace_posix(
                    temporary_name,
                    path,
                    expected_etag,
                    mutation_context,
                )
        except AtomicReplaceError as exc:
            if exc.context.get("preserve_temporary") or exc.context.get("temporary_consumed"):
                temporary_name = None
            raise
    finally:
        if temporary_name:
            # Publication and conflict results have already been decided. A
            # cleanup failure may leave an unpredictable dot-file, but must not
            # turn a successful state commit into an apparent write failure.
            _best_effort_unlink(temporary_name)


def _replace_windows(
    temporary_name: str,
    path: Path,
    expected_etag: str,
    context: dict[str, Any] | None,
) -> str | None:
    if not _entry_exists(path):
        if expected_etag != EMPTY_ETAG:
            raise _conflict(
                path,
                expected_etag,
                EMPTY_ETAG,
                context,
                "file disappeared before atomic replacement",
            )
        try:
            _windows_move_no_replace(temporary_name, path)
        except OSError as exc:
            error_number = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
            if error_number in _WINDOWS_ALREADY_EXISTS or _entry_exists(path):
                _, current_etag = _read_snapshot(path)
                raise _conflict(
                    path,
                    expected_etag,
                    current_etag,
                    context,
                    "file appeared before atomic creation",
                ) from exc
            raise AtomicReplaceError(
                "cas_unavailable",
                "Windows atomic creation could not be completed safely",
                retryable=True,
                context=_error_context(path, {"winerror": error_number, **(context or {})}),
            ) from exc
        return None

    candidate_etag = file_etag(Path(temporary_name).read_bytes())
    backup_path = _artifact_path(path, "cas-old")
    try:
        _windows_replace_with_backup(temporary_name, path, backup_path)
    except OSError as exc:
        error_number = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
        if error_number in _WINDOWS_NOT_FOUND or not _entry_exists(path):
            raise _conflict(
                path,
                expected_etag,
                EMPTY_ETAG,
                context,
                "file disappeared before atomic replacement",
            ) from exc
        try:
            _, current_etag = _read_snapshot(path)
        except AtomicReplaceError:
            current_etag = ""
        raise AtomicReplaceError(
            "replace_failed",
            "file could not be atomically replaced",
            retryable=True,
            context=_error_context(
                path,
                {
                    "winerror": error_number,
                    "current_file_etag": current_etag,
                    "expected_file_etag": expected_etag,
                    **(context or {}),
                },
            ),
        ) from exc

    # ReplaceFileW moved the old canonical file to backup_path. Verifying that
    # displaced file closes the FILE_SHARE_DELETE race left by a read guard.
    try:
        _, previous_etag = _read_snapshot(backup_path)
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "the displaced file could not be verified; recovery content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "expected_file_etag": expected_etag,
                    "recovery_path": str(backup_path),
                    "temporary_consumed": True,
                    **(context or {}),
                },
            ),
        ) from exc

    if previous_etag == expected_etag:
        _best_effort_unlink(backup_path)
        return None

    try:
        _, current_etag = _read_snapshot(path)
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "the canonical file could not be inspected; displaced content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "recovery_path": str(backup_path),
                    "temporary_consumed": True,
                    **(context or {}),
                },
            ),
        ) from exc

    if current_etag != candidate_etag:
        # Another writer already replaced our candidate. Keep its canonical
        # update in place and retain the earlier displaced external version.
        raise _conflict(
            path,
            expected_etag,
            current_etag,
            context,
            "file changed during compare-and-swap; external content was preserved",
            previous_file_etag=previous_etag,
            candidate_file_etag=candidate_etag,
            recovery_path=str(backup_path),
            temporary_consumed=True,
        )

    recovery_path = _artifact_path(path, "cas-recovery")
    try:
        _windows_replace_with_backup(str(backup_path), path, recovery_path)
    except OSError as exc:
        error_number = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
        raise AtomicReplaceError(
            "cas_restore_failed",
            "file changed before atomic replacement; displaced content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "winerror": error_number,
                    "current_file_etag": current_etag,
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "candidate_file_etag": candidate_etag,
                    "recovery_path": str(backup_path),
                    "temporary_consumed": True,
                    **(context or {}),
                },
            ),
        ) from exc

    # The rollback itself is an exchange: whatever occupied the canonical path
    # at that instant is now recoverable here rather than being overwritten.
    try:
        _, recovery_etag = _read_snapshot(recovery_path)
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "rollback completed but its recovery file could not be verified",
            retryable=True,
            context=_error_context(
                path,
                {
                    "current_file_etag": previous_etag,
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "candidate_file_etag": candidate_etag,
                    "recovery_path": str(recovery_path),
                    "temporary_consumed": True,
                    **(context or {}),
                },
            ),
        ) from exc

    extra: dict[str, Any] = {"temporary_consumed": True}
    if recovery_etag == candidate_etag:
        _best_effort_unlink(recovery_path)
    else:
        extra["recovery_path"] = str(recovery_path)
        extra["recovery_file_etag"] = recovery_etag
    raise _conflict(
        path,
        expected_etag,
        previous_etag,
        context,
        "file changed before atomic replacement; displaced content was restored",
        previous_file_etag=previous_etag,
        candidate_file_etag=candidate_etag,
        **extra,
    )


def _replace_posix(
    temporary_name: str,
    path: Path,
    expected_etag: str,
    context: dict[str, Any] | None,
) -> str | None:
    if not _entry_exists(path):
        if expected_etag != EMPTY_ETAG:
            # A deleted expected file is a conflict, never permission to
            # publish the candidate under the now-vacant name.
            raise _conflict(
                path,
                expected_etag,
                EMPTY_ETAG,
                context,
                "file disappeared before atomic replacement",
            )
        try:
            _posix_move_no_replace(Path(temporary_name), path)
        except AtomicReplaceError:
            raise
        except OSError as exc:
            if exc.errno in {errno.EEXIST, errno.ENOTEMPTY} or _entry_exists(path):
                _, current_etag = _read_snapshot(path)
                raise _conflict(
                    path,
                    expected_etag,
                    current_etag,
                    context,
                    "file appeared before atomic creation",
                ) from exc
            raise AtomicReplaceError(
                "cas_unavailable",
                "POSIX atomic creation could not be completed safely",
                retryable=True,
                context=_error_context(path, {"errno": exc.errno, **(context or {})}),
            ) from exc
        return None

    candidate_etag = file_etag(Path(temporary_name).read_bytes())
    try:
        _posix_exchange(Path(temporary_name), path)
    except AtomicReplaceError:
        raise
    except OSError as exc:
        if exc.errno == errno.ENOENT or not _entry_exists(path):
            raise _conflict(
                path,
                expected_etag,
                EMPTY_ETAG,
                context,
                "file disappeared before atomic replacement",
            ) from exc
        raise AtomicReplaceError(
            "replace_failed",
            "POSIX compare-and-swap failed",
            retryable=True,
            context=_error_context(path, {"errno": exc.errno, **(context or {})}),
        ) from exc

    try:
        _, previous_etag = _read_snapshot(Path(temporary_name))
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "the displaced file could not be verified; recovery content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "expected_file_etag": expected_etag,
                    "recovery_path": temporary_name,
                    "preserve_temporary": True,
                    **(context or {}),
                },
            ),
        ) from exc

    if previous_etag == expected_etag:
        _best_effort_unlink(temporary_name)
        return None

    try:
        _, current_etag = _read_snapshot(path)
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "the canonical file could not be inspected; displaced content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "candidate_file_etag": candidate_etag,
                    "recovery_path": temporary_name,
                    "preserve_temporary": True,
                    **(context or {}),
                },
            ),
        ) from exc

    if current_etag != candidate_etag:
        # The canonical path already contains a newer external write. Do not
        # exchange it away merely to restore the older displaced version.
        raise _conflict(
            path,
            expected_etag,
            current_etag,
            context,
            "file changed during compare-and-swap; external content was preserved",
            previous_file_etag=previous_etag,
            candidate_file_etag=candidate_etag,
            recovery_path=temporary_name,
            preserve_temporary=True,
        )

    try:
        _posix_exchange(Path(temporary_name), path)
    except (AtomicReplaceError, OSError) as exc:
        error_number = getattr(exc, "errno", None)
        raise AtomicReplaceError(
            "cas_restore_failed",
            "file changed before atomic replacement; displaced content was preserved",
            retryable=True,
            context=_error_context(
                path,
                {
                    "errno": error_number,
                    "current_file_etag": current_etag,
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "candidate_file_etag": candidate_etag,
                    "recovery_path": temporary_name,
                    "preserve_temporary": True,
                    **(context or {}),
                },
            ),
        ) from exc

    try:
        _, recovery_etag = _read_snapshot(Path(temporary_name))
    except AtomicReplaceError as exc:
        raise AtomicReplaceError(
            "cas_restore_failed",
            "rollback completed but its recovery file could not be verified",
            retryable=True,
            context=_error_context(
                path,
                {
                    "current_file_etag": previous_etag,
                    "expected_file_etag": expected_etag,
                    "previous_file_etag": previous_etag,
                    "candidate_file_etag": candidate_etag,
                    "recovery_path": temporary_name,
                    "preserve_temporary": True,
                    **(context or {}),
                },
            ),
        ) from exc

    extra: dict[str, Any] = {}
    if recovery_etag == candidate_etag:
        _best_effort_unlink(temporary_name)
    else:
        extra.update(
            {
                "recovery_path": temporary_name,
                "recovery_file_etag": recovery_etag,
                "preserve_temporary": True,
            }
        )
    raise _conflict(
        path,
        expected_etag,
        previous_etag,
        context,
        "file changed before atomic replacement; displaced content was restored",
        previous_file_etag=previous_etag,
        candidate_file_etag=candidate_etag,
        **extra,
    )


def _posix_move_no_replace(source: Path, target: Path) -> None:
    if sys.platform.startswith("linux"):
        _linux_rename(source, target, _RENAME_NOREPLACE)
        return
    if sys.platform == "darwin":
        _darwin_rename(source, target, _RENAME_EXCL)
        return
    raise AtomicReplaceError(
        "cas_unavailable",
        "this POSIX platform has no verified atomic no-replace primitive",
        retryable=True,
        context=_error_context(target),
    )


def _posix_exchange(source: Path, target: Path) -> None:
    if sys.platform.startswith("linux"):
        _linux_rename(source, target, _RENAME_EXCHANGE)
        return
    if sys.platform == "darwin":
        _darwin_rename(source, target, _RENAME_SWAP)
        return
    raise AtomicReplaceError(
        "cas_unavailable",
        "this POSIX platform has no verified atomic exchange primitive",
        retryable=True,
        context=_error_context(target),
    )


def _linux_rename(source: Path, target: Path, flags: int) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as exc:
        raise AtomicReplaceError(
            "cas_unavailable",
            "renameat2 is unavailable; refusing an unsafe replacement",
            retryable=True,
            context=_error_context(target),
        ) from exc
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(target),
        flags,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {
            errno.ENOSYS,
            errno.EINVAL,
            errno.EXDEV,
            getattr(errno, "ENOTSUP", errno.EINVAL),
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }:
            raise AtomicReplaceError(
                "cas_unavailable",
                "renameat2 operation is unavailable; refusing an unsafe replacement",
                retryable=True,
                context=_error_context(target, {"errno": error_number}),
            )
        raise OSError(error_number, "renameat2 failed")


def _darwin_rename(source: Path, target: Path, flags: int) -> None:
    try:
        renamex_np = ctypes.CDLL(None, use_errno=True).renamex_np
    except (AttributeError, OSError) as exc:
        raise AtomicReplaceError(
            "cas_unavailable",
            "renamex_np is unavailable; refusing an unsafe replacement",
            retryable=True,
            context=_error_context(target),
        ) from exc
    renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    renamex_np.restype = ctypes.c_int
    result = renamex_np(os.fsencode(source), os.fsencode(target), flags)
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {
            errno.ENOSYS,
            errno.EINVAL,
            errno.EXDEV,
            getattr(errno, "ENOTSUP", errno.EINVAL),
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }:
            raise AtomicReplaceError(
                "cas_unavailable",
                "renamex_np operation is unavailable; refusing an unsafe replacement",
                retryable=True,
                context=_error_context(target, {"errno": error_number}),
            )
        raise OSError(error_number, "renamex_np failed")


def _windows_move_no_replace(temporary_name: str, path: Path) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file = kernel32.MoveFileExW
    move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    move_file.restype = ctypes.c_int
    if not move_file(str(temporary_name), str(path), 0x00000008):
        error_number = ctypes.get_last_error()
        raise OSError(error_number, "MoveFileExW failed", str(path), error_number)


def _windows_replace_with_backup(
    replacement_name: str,
    path: Path,
    backup_path: Path,
) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    replace_file = kernel32.ReplaceFileW
    replace_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    replace_file.restype = ctypes.c_int
    if not replace_file(
        str(path),
        str(replacement_name),
        str(backup_path),
        0,
        None,
        None,
    ):
        error_number = ctypes.get_last_error()
        raise OSError(error_number, "ReplaceFileW failed", str(path), error_number)
