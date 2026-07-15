#!/usr/bin/env python3
"""Adversarial safety and privacy regressions for Nature memory."""

from __future__ import annotations

import os
import errno
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory as memory  # noqa: E402


def workflow(base: Path, name: str = "wf") -> Path:
    path = base / "docs" / "nature-workflows" / name
    path.mkdir(parents=True)
    (path / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
    return path


class MemorySafetyTests(unittest.TestCase):
    def test_control_sentinel_and_known_secret_inputs_fail_before_write(self) -> None:
        cases = [
            ("control", "safe\x00body", "control_character"),
            ("sentinel", memory.SENTINEL_START, "sentinel_injection"),
            ("secret", "sk-live-test-secret", "secret_format"),
            ("pem", "-----BEGIN PRIVATE KEY-----", "secret_format"),
        ]
        for title, body, code in cases:
            with self.subTest(title=title), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                wf = workflow(root)
                result = memory.command_memory_remember(
                    root, wf, "shared", title, body, {"kind": "decision"}
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], code)
                self.assertFalse((wf / "memory.md").exists())

    def test_local_scope_fail_closed_does_not_touch_gitignore_or_shared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root)
            subprocess.run(["git", "init", str(root)], capture_output=True, check=True)
            local = wf / "memory.local.md"
            before_gitignore = (root / ".gitignore").exists()
            result = memory.command_memory_remember(
                root, wf, "local", "private", "private body", {"kind": "decision"}
            )
            self.assertFalse(result["ok"])
            self.assertIn(result["error"]["code"], {"local_scope_not_ignored", "local_scope_git_failed"})
            self.assertFalse(local.exists())
            self.assertEqual((root / ".gitignore").exists(), before_gitignore)
            self.assertFalse((wf / "memory.md").exists())

    def test_shared_recall_excludes_local_and_preserves_crlf_and_nfd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root)
            shared = memory.command_memory_remember(
                root, wf, "shared", "café 约束", "shared body", {"kind": "constraint"}
            )
            self.assertTrue(shared["ok"], shared)
            local_id = "nm_1234567890ab4cde8f0123456789abcd"
            local_text = memory.serialize_entry(
                "私密约束",
                "local-only body",
                {
                    "schema": 1,
                    "id": local_id,
                    "kind": "constraint",
                    "lifecycle": "active",
                    "provenance": "user",
                    "created_at": "2026-07-14T07:00:00Z",
                    "updated_at": "2026-07-14T07:00:00Z",
                },
            ).replace("\n", "\r\n")
            (wf / "memory.local.md").write_bytes(local_text.encode("utf-8"))

            query = unicodedata.normalize("NFD", "café")
            recalled = memory.command_memory_recall(root, wf, "shared", query)
            self.assertEqual(recalled["results"][0]["id"], shared["entry_id"])
            self.assertNotIn("local-only body", str(recalled))
            parsed_local = memory.parse_memory_document((wf / "memory.local.md").read_text(encoding="utf-8"), wf / "memory.local.md")
            self.assertEqual(parsed_local.entries[0].entry_id, local_id)

    def test_malformed_sentinel_and_duplicate_legacy_alias_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root)
            agents = root / "AGENTS.md"
            agents.write_text(f"{memory.SENTINEL_START}\nold\n", encoding="utf-8")
            before = agents.read_bytes()
            repaired = memory.command_memory_index(base=root)
            self.assertFalse(repaired["ok"])
            self.assertEqual(repaired["error"]["code"], "malformed_sentinel")
            self.assertEqual(agents.read_bytes(), before)

            path = wf / "memory.md"
            path.write_text(
                "## M1 · one\nold\n\n## M1 · two\nold\n", encoding="utf-8"
            )
            original = path.read_bytes()
            migrated = memory.command_memory_migrate(root, wf, "shared")
            self.assertFalse(migrated["ok"])
            self.assertEqual(migrated["error"]["code"], "ambiguous_legacy_ref")
            self.assertEqual(path.read_bytes(), original)

    def test_symlink_escape_is_rejected_when_platform_allows_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            wf = workflow(root)
            outside = Path(tmp) / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            try:
                os.symlink(outside, wf / "memory.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(memory.MemoryBoundaryError) as error:
                memory.resolve_memory_path(root, wf, "shared")
            self.assertEqual(error.exception.code, "path_symlink_escape")

    def test_lock_symlink_escape_is_rejected_when_platform_allows_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            wf = workflow(root)
            outside = Path(tmp) / "outside.lock"
            outside.write_bytes(b"outside")
            try:
                os.symlink(outside, wf / ".nature-memory.lock")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(memory.MemoryBoundaryError) as error:
                with memory.workflow_memory_lock(wf):
                    pass
            self.assertIn(error.exception.code, {"path_symlink_escape", "path_hardlink_escape"})
            self.assertEqual(outside.read_bytes(), b"outside")

    def test_symlink_boundary_rejection_branch_has_deterministic_fallback_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            wf = workflow(root)
            # This keeps the boundary branch executable even when Windows
            # symlink creation is disabled by the host privilege policy.
            with patch.object(memory.Path, "is_symlink", return_value=True):
                with self.assertRaises(memory.MemoryBoundaryError) as error:
                    memory.resolve_memory_path(root, wf, "shared")
            self.assertEqual(error.exception.code, "path_symlink_escape")

    def test_memory_hardlink_is_rejected_before_external_content_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            wf = workflow(root)
            outside = Path(tmp) / "outside.md"
            outside.write_text("## external\nexternal body\n", encoding="utf-8")
            try:
                os.link(outside, wf / "memory.md")
            except OSError as exc:
                self.skipTest(f"hardlink unavailable: {exc}")
            with self.assertRaises(memory.MemoryBoundaryError) as error:
                memory.resolve_memory_path(root, wf, "shared")
            self.assertEqual(error.exception.code, "path_hardlink_escape")

    def test_agents_backup_uses_exclusive_create_and_does_not_follow_external_hardlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            wf = workflow(root)
            memory_path = wf / "memory.md"
            memory_path.write_text(memory.serialize_entry("entry", "body", {
                "schema": 1,
                "id": "nm_1234567890ab4cde8f0123456789abcd",
                "kind": "decision",
                "lifecycle": "active",
                "provenance": "user",
                "created_at": "2026-07-14T07:00:00Z",
                "updated_at": "2026-07-14T07:00:00Z",
            }), encoding="utf-8")
            agents = root / "AGENTS.md"
            agents.write_text("original", encoding="utf-8")
            external = Path(tmp) / "external-backup-target"
            external.write_text("must remain", encoding="utf-8")
            os.link(external, root / "AGENTS.md.nature-memory.bak")
            result = memory.command_memory_index(base=root)
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "agents_backup_exists")
            self.assertEqual(external.read_text(encoding="utf-8"), "must remain")

    def test_lock_backend_permission_failure_is_not_reported_as_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root)

            def permission_failure(fd: int, operation: int) -> None:
                raise OSError(errno.EPERM, "permission denied")

            fake_fcntl = type("Fcntl", (), {"LOCK_EX": 1, "LOCK_NB": 2, "LOCK_UN": 4, "flock": permission_failure})
            with patch.object(memory, "_uses_windows_lock_backend", return_value=False), patch.dict(sys.modules, {"fcntl": fake_fcntl}):
                with self.assertRaises(memory.MemoryBoundaryError) as error:
                    with memory.workflow_memory_lock(wf, timeout=0.01):
                        pass
            self.assertEqual(error.exception.code, "lock_unavailable")

    def test_lock_file_links_are_rejected_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root)
            outside = root / "outside.lock"
            outside.write_bytes(b"0")
            lock = wf / ".nature-memory.lock"
            try:
                os.link(outside, lock)
            except OSError as exc:
                self.skipTest(f"hardlink unavailable: {exc}")
            with self.assertRaises(memory.MemoryBoundaryError) as error:
                with memory.workflow_memory_lock(wf):
                    pass
            self.assertEqual(error.exception.code, "path_hardlink_escape")


if __name__ == "__main__":
    unittest.main()
