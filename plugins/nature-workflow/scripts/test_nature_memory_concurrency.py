#!/usr/bin/env python3
"""Concurrency and atomic-replace regressions for Nature memory."""

from __future__ import annotations

import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory as memory  # noqa: E402


def workflow(base: Path, name: str) -> Path:
    path = base / "docs" / "nature-workflows" / name
    path.mkdir(parents=True)
    (path / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
    return path


def create(root: Path, wf: Path, title: str) -> dict:
    result = memory.command_memory_remember(root, wf, "shared", title, "body", {"kind": "decision"})
    if not result["ok"]:
        raise AssertionError(result)
    return result


def process_update(root_text: str, workflow_text: str, entry_id: str, etag: str, title: str, output) -> None:
    root = Path(root_text)
    workflow_dir = Path(workflow_text)
    result = memory.command_memory_remember(
        root,
        workflow_dir,
        "shared",
        title,
        title,
        {"kind": "decision"},
        entry_id=entry_id,
        expected_etag=etag,
    )
    output.put(result)


class MemoryConcurrencyTests(unittest.TestCase):
    def test_fcntl_lock_backend_is_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root, "fcntl")
            calls: list[tuple[int, int]] = []

            def fake_flock(fd: int, operation: int) -> None:
                calls.append((fd, operation))

            fake_fcntl = SimpleNamespace(
                LOCK_EX=1,
                LOCK_NB=2,
                LOCK_UN=4,
                flock=fake_flock,
            )
            with patch.object(memory, "_uses_windows_lock_backend", return_value=False), patch.dict(sys.modules, {"fcntl": fake_fcntl}):
                with memory.workflow_memory_lock(wf):
                    pass
            self.assertEqual([operation for _, operation in calls], [3, 4])

    def test_different_entry_updates_do_not_lose_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root, "wf")
            first = create(root, wf, "first")
            second = create(root, wf, "second")

            def update(item: dict, title: str) -> dict:
                return memory.command_memory_remember(
                    root,
                    wf,
                    "shared",
                    title,
                    "updated body",
                    {"kind": "decision"},
                    entry_id=item["entry_id"],
                    expected_etag=item["etag"],
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda args: update(*args), [(first, "first updated"), (second, "second updated")]))

            self.assertTrue(all(result["ok"] for result in results), results)
            entries = memory.parse_memory((wf / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual({entry.title for entry in entries}, {"first updated", "second updated"})
            self.assertEqual(len(list(wf.glob("*.tmp"))), 0)
            self.assertEqual(len(list(wf.glob(".*.tmp"))), 0)

    def test_same_entry_stale_etag_has_one_winner_and_one_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root, "wf")
            initial = create(root, wf, "same")

            def update(title: str) -> dict:
                return memory.command_memory_remember(
                    root,
                    wf,
                    "shared",
                    title,
                    title,
                    {"kind": "decision"},
                    entry_id=initial["entry_id"],
                    expected_etag=initial["etag"],
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(update, ["winner one", "winner two"]))

            self.assertEqual(sum(result["ok"] for result in results), 1, results)
            self.assertEqual(
                sum(result.get("error", {}).get("code") == "etag_conflict" for result in results),
                1,
                results,
            )
            parsed = memory.parse_memory((wf / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual(len(parsed), 1)
            self.assertIn(parsed[0].title, {"winner one", "winner two"})

    def test_different_workflows_are_independent_under_parallel_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_wf = workflow(root, "first")
            second_wf = workflow(root, "second")
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(
                        lambda args: create(root, *args),
                        [(first_wf, "one"), (second_wf, "two")],
                    )
                )
            self.assertTrue(all(result["ok"] for result in results), results)
            self.assertEqual(len(memory.parse_memory((first_wf / "memory.md").read_text(encoding="utf-8"))), 1)
            self.assertEqual(len(memory.parse_memory((second_wf / "memory.md").read_text(encoding="utf-8"))), 1)

    def test_separate_processes_share_the_same_cas_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = workflow(root, "process")
            initial = create(root, wf, "same process")
            context = multiprocessing.get_context("spawn")
            queue = context.Queue()
            processes = [
                context.Process(
                    target=process_update,
                    args=(str(root), str(wf), initial["entry_id"], initial["etag"], title, queue),
                )
                for title in ("process winner one", "process winner two")
            ]
            for process in processes:
                process.start()
            results = [queue.get(timeout=30) for _ in processes]
            for process in processes:
                process.join(timeout=30)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum(item.get("ok", False) for item in results), 1, results)
            self.assertEqual(sum(item.get("error", {}).get("code") == "etag_conflict" for item in results), 1, results)


if __name__ == "__main__":
    unittest.main()
