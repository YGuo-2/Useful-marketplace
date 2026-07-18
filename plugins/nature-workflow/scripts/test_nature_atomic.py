#!/usr/bin/env python3
"""Targeted concurrency tests for nature_atomic."""

from __future__ import annotations

import ctypes
import errno
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nature_atomic as atomic


def _fake_exchange(source: Path, target: Path) -> None:
    scratch = source.with_name(source.name + ".fake-swap")
    os.replace(source, scratch)
    os.replace(target, source)
    os.replace(scratch, target)


class AtomicReplaceTests(unittest.TestCase):
    def test_posix_deleted_nonempty_expected_is_conflict_not_create(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            candidate = root / ".candidate.tmp"
            candidate.write_bytes(b"candidate")

            with self.assertRaises(atomic.AtomicReplaceError) as raised:
                atomic._replace_posix(
                    str(candidate),
                    target,
                    atomic.file_etag(b"expected-old"),
                    None,
                )

            self.assertEqual(raised.exception.code, "file_changed_outside_lock")
            self.assertEqual(raised.exception.context["current_file_etag"], atomic.EMPTY_ETAG)
            self.assertFalse(target.exists())
            self.assertEqual(candidate.read_bytes(), b"candidate")

    def test_posix_restore_exchange_preserves_intervening_update(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            candidate = root / ".candidate.tmp"
            target.write_bytes(b"unexpected-before-exchange")
            candidate.write_bytes(b"candidate")
            calls = 0

            def exchange_with_restore_race(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    destination.write_bytes(b"external-during-restore")
                _fake_exchange(source, destination)

            with patch.object(atomic, "_posix_exchange", side_effect=exchange_with_restore_race):
                with self.assertRaises(atomic.AtomicReplaceError) as raised:
                    atomic._replace_posix(
                        str(candidate),
                        target,
                        atomic.file_etag(b"expected-old"),
                        None,
                    )

            self.assertEqual(raised.exception.code, "file_changed_outside_lock")
            self.assertEqual(target.read_bytes(), b"unexpected-before-exchange")
            recovery = Path(raised.exception.context["recovery_path"])
            self.assertEqual(recovery, candidate)
            self.assertEqual(recovery.read_bytes(), b"external-during-restore")

    def test_posix_does_not_restore_over_newer_canonical_update(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            candidate = root / ".candidate.tmp"
            target.write_bytes(b"unexpected-before-exchange")
            candidate.write_bytes(b"candidate")
            real_read = atomic._read_snapshot
            target_reads = 0

            def read_with_race(path: Path) -> tuple[bytes, str]:
                nonlocal target_reads
                if Path(path) == target:
                    target_reads += 1
                    if target_reads == 1:
                        target.write_bytes(b"newer-canonical")
                return real_read(Path(path))

            with patch.object(atomic, "_posix_exchange", side_effect=_fake_exchange), patch.object(
                atomic, "_read_snapshot", side_effect=read_with_race
            ):
                with self.assertRaises(atomic.AtomicReplaceError) as raised:
                    atomic._replace_posix(
                        str(candidate),
                        target,
                        atomic.file_etag(b"expected-old"),
                        None,
                    )

            self.assertEqual(raised.exception.code, "file_changed_outside_lock")
            self.assertEqual(target.read_bytes(), b"newer-canonical")
            self.assertEqual(candidate.read_bytes(), b"unexpected-before-exchange")
            self.assertTrue(raised.exception.context["preserve_temporary"])

    def test_cleanup_failure_after_success_is_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            target.write_bytes(b"old")
            real_unlink = atomic.os.unlink

            def deny_internal_cleanup(path: str | Path, *args: object, **kwargs: object) -> None:
                if ".cas-old." in str(path):
                    raise PermissionError("forced cleanup failure")
                real_unlink(path, *args, **kwargs)

            if os.name == "nt":
                with patch.object(atomic.os, "unlink", side_effect=deny_internal_cleanup):
                    atomic.atomic_replace_text(
                        target,
                        "new",
                        expected_etag=atomic.file_etag(b"old"),
                    )
            else:
                with patch.object(atomic.os, "unlink", side_effect=deny_internal_cleanup):
                    atomic.atomic_replace_text(
                        target,
                        "new",
                        expected_etag=atomic.file_etag(b"old"),
                    )
            self.assertEqual(target.read_bytes(), b"new")

    @unittest.skipUnless(os.name == "nt", "requires real Windows ReplaceFileW")
    def test_windows_replace_race_is_detected_and_external_content_restored(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            target.write_bytes(b"expected-old")
            ready = threading.Event()
            raced = threading.Event()
            errors: list[BaseException] = []
            real_replace = atomic._windows_replace_with_backup
            first = True

            def delayed_replace(replacement: str, destination: Path, backup: Path) -> None:
                nonlocal first
                if first:
                    first = False
                    ready.set()
                    self.assertTrue(raced.wait(5), "external writer did not finish")
                real_replace(replacement, destination, backup)

            def external_writer() -> None:
                try:
                    self.assertTrue(ready.wait(5), "CAS did not reach exchange")
                    external = root / ".external.tmp"
                    external.write_bytes(b"external-update")
                    external_backup = root / ".external-old.bak"
                    real_replace(str(external), target, external_backup)
                    atomic._best_effort_unlink(external_backup)
                except BaseException as exc:  # pragma: no cover - assertion relay
                    errors.append(exc)
                finally:
                    raced.set()

            thread = threading.Thread(target=external_writer)
            thread.start()
            try:
                with patch.object(atomic, "_windows_replace_with_backup", side_effect=delayed_replace):
                    with self.assertRaises(atomic.AtomicReplaceError) as raised:
                        atomic.atomic_replace_text(
                            target,
                            "candidate",
                            expected_etag=atomic.file_etag(b"expected-old"),
                        )
            finally:
                thread.join(5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(raised.exception.code, "file_changed_outside_lock")
            self.assertEqual(target.read_bytes(), b"external-update")

    def test_darwin_uses_renamex_np_swap(self) -> None:
        class FakeFunction:
            def __init__(self) -> None:
                self.calls: list[tuple[object, ...]] = []

            def __call__(self, *args: object) -> int:
                self.calls.append(args)
                return 0

        class FakeLibC:
            def __init__(self) -> None:
                self.renamex_np = FakeFunction()

        libc = FakeLibC()
        with patch.object(atomic.sys, "platform", "darwin"), patch.object(
            atomic.ctypes, "CDLL", return_value=libc
        ):
            atomic._posix_exchange(Path("source"), Path("target"))

        self.assertEqual(len(libc.renamex_np.calls), 1)
        self.assertEqual(libc.renamex_np.calls[0][2], atomic._RENAME_SWAP)

    def test_unsupported_posix_exchange_fails_closed(self) -> None:
        with patch.object(atomic.sys, "platform", "freebsd14"):
            with self.assertRaises(atomic.AtomicReplaceError) as raised:
                atomic._posix_exchange(Path("source"), Path("target"))
        self.assertEqual(raised.exception.code, "cas_unavailable")

    def test_native_exchange_unavailable_fails_closed(self) -> None:
        class MissingLibC:
            pass

        with patch.object(atomic.sys, "platform", "darwin"), patch.object(
            atomic.ctypes, "CDLL", return_value=MissingLibC()
        ):
            with self.assertRaises(atomic.AtomicReplaceError) as raised:
                atomic._posix_exchange(Path("source"), Path("target"))
        self.assertEqual(raised.exception.code, "cas_unavailable")

    def test_posix_exchange_os_error_does_not_fallback_to_replace(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            target = root / "state.yml"
            candidate = root / ".candidate.tmp"
            target.write_bytes(b"old")
            candidate.write_bytes(b"new")
            with patch.object(atomic, "_posix_exchange", side_effect=OSError(errno.EIO, "forced")), patch.object(
                atomic.os, "replace", side_effect=AssertionError("unsafe fallback")
            ):
                with self.assertRaises(atomic.AtomicReplaceError) as raised:
                    atomic._replace_posix(
                        str(candidate),
                        target,
                        atomic.file_etag(b"old"),
                        None,
                    )
            self.assertEqual(raised.exception.code, "replace_failed")
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(candidate.read_bytes(), b"new")


if __name__ == "__main__":
    unittest.main(verbosity=2)
