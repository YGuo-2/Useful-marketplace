#!/usr/bin/env python3
"""Tests for the Nature workflow state engine (task lifecycle + status)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_progress as np  # noqa: E402
import nature_context as nc  # noqa: E402
import nature_memory  # noqa: E402


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

    # --- read commands are side-effect free ------------------------------

    def test_status_does_not_mutate_disk(self) -> None:
        wf = self.make(["T1: first", "T2: second"])
        np.command_start(None, wf, "T1", base=self.base)
        before = (Path(wf) / "nature.yml").read_text(encoding="utf-8")
        np.command_status(None, wf, base=self.base)
        np.command_resume(None, wf, base=self.base)
        after = (Path(wf) / "nature.yml").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_nature_progress_remains_independent_from_memory_module(self) -> None:
        source = (SCRIPT_DIR / "nature_progress.py").read_text(encoding="utf-8")
        self.assertNotIn("nature_memory", source)

    def test_resume_with_memory_parses_canonical_file_once(self) -> None:
        wf = self.make(["T1: collect evidence"])
        nature_memory.command_memory_remember(
            self.base,
            wf,
            "shared",
            "collect evidence decision",
            "use the source ledger",
            {"kind": "decision"},
        )
        original = nature_memory.parse_memory_document
        calls = 0

        def counted(text: str, source_path=None):
            nonlocal calls
            calls += 1
            return original(text, source_path)

        with patch.object(nature_memory, "parse_memory_document", side_effect=counted):
            result = nc.resume_with_memory(project_root=self.base, workflow_dir=wf)

        self.assertTrue(result["ok"], result)
        self.assertEqual(calls, 1)
        self.assertIn(result["memory_context"]["status"], {"available", "partial"})

    def test_resume_with_memory_preserves_partial_parse_errors(self) -> None:
        wf = self.make(["T1: collect evidence"])
        metadata = {
            "schema": 1,
            "id": "nm_f47ac10b58cc4372a5670e02b2c3d479",
            "kind": "decision",
            "lifecycle": "active",
            "provenance": "user",
            "created_at": "2026-07-14T07:00:00Z",
            "updated_at": "2026-07-14T07:00:00Z",
        }
        text = nature_memory.serialize_entry("collect evidence", "first", metadata)
        text += nature_memory.serialize_entry("duplicate evidence", "second", metadata)
        (Path(wf) / "memory.md").write_text(text, encoding="utf-8")

        result = nc.resume_with_memory(project_root=self.base, workflow_dir=wf, query="collect evidence")
        context = result["memory_context"]
        self.assertEqual(context["status"], "partial")
        self.assertTrue(context["results"], context)
        self.assertEqual(context["error"]["code"], "memory_parse_errors")
        self.assertIn("duplicate_id", {item["code"] for item in context["diagnostics"]})
        self.assertIn("duplicate_id", {item["code"] for item in context["error"]["diagnostics"]})

    def test_resume_memory_failure_is_partial_without_changing_progress(self) -> None:
        wf = self.make(["T1: collect evidence"])
        with patch.object(nc, "_load_memory_context", side_effect=RuntimeError("unavailable")):
            result = nc.resume_with_memory(project_root=self.base, workflow_dir=wf)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["progress"]["resume_state"], "ready")
        self.assertEqual(result["memory_context"]["status"], "unavailable")

    def test_partial_facade_context_respects_requested_byte_budget(self) -> None:
        wf = self.make(["T1: collect evidence"])
        metadata = {
            "schema": 1,
            "id": "nm_f47ac10b58cc4372a5670e02b2c3d479",
            "kind": "decision",
            "lifecycle": "active",
            "provenance": "user",
            "created_at": "2026-07-14T07:00:00Z",
            "updated_at": "2026-07-14T07:00:00Z",
        }
        text = nature_memory.serialize_entry("collect evidence", "first", metadata)
        text += "\n".join(f"## malformed-{index}\n<!-- nature-memory: {{}} -->\nbody\n" for index in range(20))
        (Path(wf) / "memory.md").write_text(text, encoding="utf-8")
        result = nc.resume_with_memory(project_root=self.base, workflow_dir=wf, query="collect evidence", max_bytes=256)
        context = result["memory_context"]
        self.assertLessEqual(len(json.dumps(context, ensure_ascii=False, separators=(",", ":")).encode("utf-8")), 256)
        self.assertIn("error", context)

    def test_unexpected_facade_exception_is_diagnosable_after_progress_commit(self) -> None:
        wf = self.make(["T1: collect evidence"])
        with patch.object(nc, "_load_memory_context", side_effect=KeyError("internal")):
            result = nc.complete_with_memory_review(
                None, wf, "T1", "complete evidence", project_root=self.base
            )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["progress_committed"])
        self.assertEqual(result["memory_review"]["error"]["code"], "memory_review_internal_error")

    def test_resume_preserves_structured_memory_error_and_requires_project_root(self) -> None:
        wf = self.make(["T1: collect evidence"])
        with patch.object(
            nature_memory,
            "command_memory_recall",
            return_value={"ok": False, "error": {"code": "invalid_utf8", "detail": "memory file must be valid UTF-8", "retryable": False}},
        ):
            result = nc.resume_with_memory(project_root=self.base, workflow_dir=wf)
        self.assertEqual(result["memory_context"]["status"], "unavailable")
        self.assertEqual(result["memory_context"]["error"]["code"], "invalid_utf8")
        with self.assertRaises(np.NatureProgressError):
            nc.resume_with_memory(workflow_dir=wf)

    def test_complete_and_block_commit_progress_before_memory_review_failure(self) -> None:
        complete_wf = self.make(["T1: complete"])
        np.command_start(None, complete_wf, "T1", base=self.base)
        with patch.object(nc, "_load_memory_context", side_effect=RuntimeError("review unavailable")):
            completed = nc.complete_with_memory_review(
                None, complete_wf, "T1", "progress evidence", project_root=self.base
            )
        self.assertTrue(completed["ok"], completed)
        self.assertTrue(completed["progress_committed"])
        self.assertEqual(completed["memory_review"]["status"], "unavailable")
        self.assertEqual(read_state(complete_wf)["tasks"][0]["status"], "completed")

        block_wf = self.make(["T1: block"])
        with patch.object(nc, "_load_memory_context", side_effect=RuntimeError("review unavailable")):
            blocked = nc.block_with_memory_review(
                None, block_wf, "T1", "waiting for source", project_root=self.base
            )
        self.assertTrue(blocked["ok"], blocked)
        self.assertTrue(blocked["progress_committed"])
        self.assertEqual(blocked["memory_review"]["status"], "unavailable")
        self.assertEqual(read_state(block_wf)["tasks"][0]["status"], "blocked")

    def test_complete_review_preserves_structured_memory_error_context(self) -> None:
        wf = self.make(["T1: complete"])
        np.command_start(None, wf, "T1", base=self.base)
        with patch.object(
            nature_memory,
            "command_memory_recall",
            return_value={
                "ok": False,
                "error": {
                    "code": "invalid_utf8",
                    "detail": "memory file must be valid UTF-8",
                    "retryable": True,
                    "memory_path": "memory.md",
                    "current_file_etag": "etag-current",
                },
            },
        ):
            result = nc.complete_with_memory_review(
                None, wf, "T1", "progress evidence", project_root=self.base
            )
        self.assertTrue(result["progress_committed"], result)
        self.assertEqual(result["memory_review"]["status"], "unavailable")
        self.assertEqual(result["memory_review"]["error"]["code"], "invalid_utf8")
        self.assertEqual(result["memory_review"]["error"]["current_file_etag"], "etag-current")


if __name__ == "__main__":
    unittest.main()
