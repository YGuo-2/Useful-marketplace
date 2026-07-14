#!/usr/bin/env python3
"""Concurrency and atomic-replace regressions for Nature memory."""

from __future__ import annotations

import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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


class MemoryConcurrencyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
