#!/usr/bin/env python3
"""Tests for the Nature workflow state engine (task lifecycle + status)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_progress as np  # noqa: E402


def read_state(workflow_dir: str) -> dict:
    return json.loads((Path(workflow_dir) / "nature.yml").read_text(encoding="utf-8"))


class StateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name).resolve()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def make(self, tasks: list[str]) -> str:
        result = np.command_new_workflow(
            None, "wf", "WF", tasks, base=self.base
        )
        return result["workflow_dir"]

    # --- basics ----------------------------------------------------------

    def test_new_then_start_is_consistent(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        started = np.command_start(None, wf, "T1", base=self.base)
        disk = read_state(wf)
        self.assertEqual(started["active_task"], "T1")
        self.assertEqual(disk["active_task"], "T1")
        self.assertEqual(disk["status"], "open")
        # progress.md mirrors disk
        progress = (Path(wf) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("Active task: T1", progress)

    # --- regression: issue #1, status/disk must not disagree ------------

    def test_block_then_start_other_keeps_status_and_disk_in_sync(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_block(None, wf, "T1", "waiting on data", base=self.base)
        # blocked does not occupy the workflow: switching to T2 is allowed
        started = np.command_start(None, wf, "T2", base=self.base)
        self.assertEqual(started["active_task"], "T2")
        self.assertEqual(started["status"], "open")

        # the core regression: a read command must agree with disk
        status = np.command_status(None, wf, base=self.base)
        disk = read_state(wf)
        self.assertEqual(status["active_task"], disk["active_task"])
        self.assertEqual(status["status"], disk["status"])
        self.assertEqual(disk["active_task"], "T2")
        # T1 stays blocked after the switch
        t1 = next(t for t in disk["tasks"] if t["id"] == "T1")
        self.assertEqual(t1["status"], "blocked")

    def test_block_surfaces_when_no_active_task(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_block(None, wf, "T1", "blocked early", base=self.base)
        disk = read_state(wf)
        self.assertEqual(disk["status"], "blocked")
        self.assertEqual(disk["active_task"], "T1")

    def test_active_wins_over_blocked_for_active_task(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_block(None, wf, "T1", "blocked", base=self.base)
        np.command_start(None, wf, "T2", base=self.base)
        disk = read_state(wf)
        # an in-progress task drives active_task even with a blocked sibling
        self.assertEqual(disk["active_task"], "T2")
        self.assertEqual(disk["status"], "open")

    # --- next_task: park a blocker and move on ---------------------------

    def test_next_task_skips_blocked_so_user_can_move_on(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_block(None, wf, "T1", "waiting on data", base=self.base)
        # blocked T1 is parked; next_task advances to the pending T2 so the
        # orchestrator's drive cycle does not stall on the blocker
        status = np.command_status(None, wf, base=self.base)
        self.assertEqual(status["next_task"]["id"], "T2")

    def test_next_task_falls_back_to_blocked_when_nothing_else(self) -> None:
        wf = self.make(["T1: only"])
        np.command_block(None, wf, "T1", "stuck", base=self.base)
        # nothing pending to move on to → still surface the blocker
        status = np.command_status(None, wf, base=self.base)
        self.assertEqual(status["next_task"]["id"], "T1")

    def test_next_task_prefers_active_over_earlier_pending(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        # start T2 out of order while the lower-index T1 is still pending
        np.command_start(None, wf, "T2", base=self.base)
        status = np.command_status(None, wf, base=self.base)
        # next_task must agree with active_task (T2), not the earlier pending T1 —
        # otherwise start(next_task) would hit the single-active guard and stall
        self.assertEqual(status["active_task"], "T2")
        self.assertEqual(status["next_task"]["id"], "T2")

    # --- completion ------------------------------------------------------

    def test_complete_all_marks_workflow_completed(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_complete(None, wf, "T1", "done T1", base=self.base)
        np.command_start(None, wf, "T2", base=self.base)
        np.command_complete(None, wf, "T2", "done T2", base=self.base)
        disk = read_state(wf)
        self.assertEqual(disk["status"], "completed")
        self.assertIsNone(disk["active_task"])

    def test_complete_active_clears_active_task(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_complete(None, wf, "T1", "evidence", base=self.base)
        disk = read_state(wf)
        # T2 still pending, no active task, workflow idle-open
        self.assertEqual(disk["status"], "open")
        self.assertIsNone(disk["active_task"])

    # --- guards ----------------------------------------------------------

    def test_start_completed_task_errors(self) -> None:
        wf = self.make(["T1: first"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_complete(None, wf, "T1", "ev", base=self.base)
        with self.assertRaises(np.NatureProgressError):
            np.command_start(None, wf, "T1", base=self.base)

    def test_start_blocked_by_other_active(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        with self.assertRaises(np.NatureProgressError):
            np.command_start(None, wf, "T2", base=self.base)

    def test_complete_requires_evidence(self) -> None:
        wf = self.make(["T1: first"])
        np.command_start(None, wf, "T1", base=self.base)
        with self.assertRaises(np.NatureProgressError):
            np.command_complete(None, wf, "T1", "   ", base=self.base)

    # --- optional format-spec gate --------------------------------------

    def test_new_workflow_spec_defaults_to_unset(self) -> None:
        wf = self.make(["T1: first"])
        disk = read_state(wf)
        self.assertEqual(disk["spec"], {"status": "unset", "source": None, "path": None})

    def test_spec_ready_records_source_and_path_and_surfaces_in_status(self) -> None:
        wf = self.make(["T1: first"])
        result = np.command_spec(None, wf, "ready", "template", base=self.base)
        self.assertEqual(result["spec"]["status"], "ready")
        self.assertEqual(result["spec"]["source"], "template")
        self.assertEqual(result["spec"]["path"], "spec.md")
        # read command surfaces the same spec state as disk
        status = np.command_status(None, wf, base=self.base)
        disk = read_state(wf)
        self.assertEqual(status["spec"], disk["spec"])
        self.assertEqual(disk["spec"]["path"], "spec.md")
        # and the human progress file mentions it
        progress = (Path(wf) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("Spec: ready (template)", progress)

    def test_spec_skipped_clears_source_and_path(self) -> None:
        wf = self.make(["T1: first"])
        np.command_spec(None, wf, "ready", "dictation", base=self.base)
        np.command_spec(None, wf, "skipped", base=self.base)
        disk = read_state(wf)
        self.assertEqual(disk["spec"], {"status": "skipped", "source": None, "path": None})

    def test_spec_rejects_invalid_status(self) -> None:
        wf = self.make(["T1: first"])
        with self.assertRaises(np.NatureProgressError):
            np.command_spec(None, wf, "bogus", base=self.base)

    def test_spec_absent_in_legacy_record_reads_as_unset(self) -> None:
        wf = self.make(["T1: first"])
        # simulate a pre-spec nature.yml written before this field existed
        state_path = Path(wf) / "nature.yml"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data.pop("spec", None)
        state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        status = np.command_status(None, wf, base=self.base)
        self.assertEqual(status["spec"], {"status": "unset", "source": None, "path": None})

    # --- add-task: dynamic sequence growth -------------------------------

    def test_add_task_appends_pending_and_surfaces_next(self) -> None:
        wf = self.make(["T1: first"])
        np.command_add_task(None, wf, "T2: second", base=self.base)
        disk = read_state(wf)
        self.assertEqual([t["id"] for t in disk["tasks"]], ["T1", "T2"])
        t2 = next(t for t in disk["tasks"] if t["id"] == "T2")
        self.assertEqual(t2["status"], "pending")
        # first pending is still T1, so next_task stays T1 (appended after it)
        status = np.command_status(None, wf, base=self.base)
        self.assertEqual(status["next_task"]["id"], "T1")

    def test_add_task_after_inserts_at_position(self) -> None:
        wf = self.make(["T1: first", "T3: third"])
        np.command_add_task(None, wf, "T2: second", after="T1", base=self.base)
        disk = read_state(wf)
        self.assertEqual([t["id"] for t in disk["tasks"]], ["T1", "T2", "T3"])

    def test_add_task_duplicate_id_errors(self) -> None:
        wf = self.make(["T1: first"])
        with self.assertRaises(np.NatureProgressError):
            np.command_add_task(None, wf, "T1: dup", base=self.base)

    def test_add_task_unknown_after_errors(self) -> None:
        wf = self.make(["T1: first"])
        with self.assertRaises(np.NatureProgressError):
            np.command_add_task(None, wf, "T2: second", after="TX", base=self.base)

    def test_add_task_auto_numbers_unlabeled(self) -> None:
        wf = self.make(["T1: first"])
        np.command_add_task(None, wf, "second, no id", base=self.base)
        disk = read_state(wf)
        # first free T{n} after the existing T1
        self.assertEqual([t["id"] for t in disk["tasks"]], ["T1", "T2"])
        self.assertEqual(disk["tasks"][1]["title"], "second, no id")

    def test_add_task_reopens_completed_workflow(self) -> None:
        wf = self.make(["T1: only"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_complete(None, wf, "T1", "done", base=self.base)
        self.assertEqual(read_state(wf)["status"], "completed")
        np.command_add_task(None, wf, "T2: more work", base=self.base)
        disk = read_state(wf)
        # a fresh pending task means the workflow is no longer completed
        self.assertEqual(disk["status"], "open")
        self.assertIsNone(disk["active_task"])

    # --- remove-task: guarded deletion -----------------------------------

    def test_remove_pending_task(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_remove_task(None, wf, "T2", base=self.base)
        disk = read_state(wf)
        self.assertEqual([t["id"] for t in disk["tasks"]], ["T1"])

    def test_remove_blocked_task_ok(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_block(None, wf, "T1", "stuck", base=self.base)
        np.command_remove_task(None, wf, "T1", base=self.base)
        disk = read_state(wf)
        self.assertEqual([t["id"] for t in disk["tasks"]], ["T2"])
        # removing the only blocker clears the blocked status
        self.assertEqual(disk["status"], "open")

    def test_remove_active_task_errors(self) -> None:
        wf = self.make(["T1: first"])
        np.command_start(None, wf, "T1", base=self.base)
        with self.assertRaises(np.NatureProgressError):
            np.command_remove_task(None, wf, "T1", base=self.base)

    def test_remove_completed_task_errors(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        np.command_complete(None, wf, "T1", "done", base=self.base)
        with self.assertRaises(np.NatureProgressError):
            np.command_remove_task(None, wf, "T1", base=self.base)

    def test_remove_unknown_task_errors(self) -> None:
        wf = self.make(["T1: first"])
        with self.assertRaises(np.NatureProgressError):
            np.command_remove_task(None, wf, "TX", base=self.base)

    # --- genre: top-level paper-type persistence -------------------------

    def test_new_with_genre_persists_and_surfaces(self) -> None:
        result = np.command_new_workflow(None, "wf", "WF", ["T1: x"], "Review", base=self.base)
        wf = result["workflow_dir"]
        disk = read_state(wf)
        self.assertEqual(disk["genre"], "review")  # normalized via slugify
        status = np.command_status(None, wf, base=self.base)
        self.assertEqual(status["genre"], "review")
        progress = (Path(wf) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("Genre: review", progress)

    def test_new_without_genre_defaults_none(self) -> None:
        wf = self.make(["T1: x"])
        self.assertIsNone(read_state(wf)["genre"])
        progress = (Path(wf) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("Genre: unset", progress)

    def test_genre_command_sets_and_changes(self) -> None:
        wf = self.make(["T1: x"])
        np.command_genre(None, wf, "research", base=self.base)
        self.assertEqual(read_state(wf)["genre"], "research")
        np.command_genre(None, wf, "methods", base=self.base)
        self.assertEqual(read_state(wf)["genre"], "methods")

    def test_genre_command_requires_value(self) -> None:
        wf = self.make(["T1: x"])
        with self.assertRaises(np.NatureProgressError):
            np.command_genre(None, wf, "   ", base=self.base)

    def test_genre_absent_in_legacy_record_reads_as_none(self) -> None:
        wf = self.make(["T1: x"])
        state_path = Path(wf) / "nature.yml"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data.pop("genre", None)
        state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        status = np.command_status(None, wf, base=self.base)
        self.assertIsNone(status["genre"])

    # --- read commands are side-effect free ------------------------------

    def test_status_does_not_mutate_disk(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        before = (Path(wf) / "nature.yml").read_text(encoding="utf-8")
        np.command_status(None, wf, base=self.base)
        np.command_resume(None, wf, base=self.base)
        after = (Path(wf) / "nature.yml").read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
