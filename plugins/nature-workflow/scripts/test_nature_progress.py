#!/usr/bin/env python3
"""Tests for the Nature workflow state engine (task lifecycle + status)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_progress as np  # noqa: E402
import nature_context as nc  # noqa: E402
import nature_memory  # noqa: E402
import nature_style  # noqa: E402


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

    def register_style_profile(self, workflow_dir: str, profile_id: str = "author-main") -> dict:
        profile_dir = Path(workflow_dir) / nature_style.PROFILE_DIR
        profile_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "id": profile_id,
            "status": "ready",
            "source_kind": "author-draft",
            "source_fingerprint": "sha256:" + "0" * 64,
            "language": "en",
            "scopes": ["global"],
            "traits": [
                {
                    "name": "sentence_rhythm",
                    "value": "medium-mixed",
                    "scope": ["global"],
                    "confidence": "high",
                    "support": 8,
                    "source_refs": ["train:results:p001", "train:discussion:p002", "train:intro:p003"],
                    "strength": "soft",
                }
            ],
            "exclusions": ["source facts", "source numbers", "source citations", "claim strength"],
        }
        profile_path = profile_dir / f"{profile_id}.md"
        profile_path.write_text(
            "# Prose Profile\n\n```json\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
            newline="",
        )
        return nature_style.command_style_register(
            self.base,
            workflow_dir,
            f"{nature_style.PROFILE_DIR}/{profile_id}.md",
        )

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

    def test_new_can_create_a_missing_workflow_root(self) -> None:
        root = self.base / "docs" / "nature-workflows"
        result = np.command_new_workflow(str(root), "wf", "WF", ["T1: first"], base=self.base)
        self.assertTrue(root.is_dir())
        self.assertEqual(Path(result["workflow_dir"]).parent, root)

    def test_missing_workflow_root_fails_closed_with_structured_error(self) -> None:
        missing = self.base / "docs" / "nature-workflows" / "missing"

        for operation in (
            lambda: np.command_discover(str(missing), base=self.base),
            lambda: np.checked_workflow_dir(None, str(missing), base=self.base),
        ):
            with self.assertRaises(np.NatureProgressError) as raised:
                operation()
            error = raised.exception
            self.assertEqual(error.code, "workflow_root_not_found")
            self.assertEqual(error.context["workflow_root"], str(missing))
            self.assertFalse(error.retryable)

    def test_memory_compatibility_paths_fail_closed_on_missing_workflow_root(self) -> None:
        missing = self.base / "docs" / "nature-workflows" / "missing"
        operations = (
            lambda: nature_memory.command_memory_check(str(missing), base=self.base, all_workflows=True),
            lambda: nature_memory.command_memory_list(str(missing), base=self.base, all_workflows=True),
            lambda: nature_memory.command_memory_recall_all(self.base, missing, "shared", "query"),
            lambda: nature_memory.command_memory_touch(str(missing), None, "M1", base=self.base),
        )

        for operation in operations:
            result = operation()
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "workflow_root_not_found")
            self.assertEqual(result["error"]["workflow_root"], str(missing))

    def test_memory_migrate_all_fails_closed_on_missing_default_workflow_root(self) -> None:
        result = nature_memory.command_memory_migrate(self.base, scope="shared", all_workflows=True)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"]["code"], "workflow_root_not_found")
        self.assertEqual(
            result["error"]["workflow_root"],
            str(self.base / "docs" / "nature-workflows"),
        )

    def test_main_emits_structured_missing_root_error(self) -> None:
        missing = self.base / "docs" / "nature-workflows" / "missing"
        with patch.dict(os.environ, {"NATURE_WORKFLOW_BASE_DIR": str(self.base)}), patch("builtins.print") as printed:
            exit_code = np.main(["discover", "--root", str(missing)])

        self.assertEqual(exit_code, 2)
        payload = json.loads(printed.call_args.args[0])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "workflow_root_not_found")
        self.assertEqual(payload["error"]["workflow_root"], str(missing))

    def test_direct_script_style_guard_error_is_structured_json(self) -> None:
        wf = self.make(["draft: Draft manuscript"])
        self.register_style_profile(wf)
        evidence = self.base / "draft.md"
        evidence.write_text("Draft text.\n", encoding="utf-8")
        env = os.environ.copy()
        env["NATURE_WORKFLOW_BASE_DIR"] = str(self.base)

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "nature_progress.py"),
                "complete",
                "draft",
                "--evidence",
                str(evidence),
                "--root",
                str(self.base / "docs" / "nature-workflows"),
                "--workflow",
                wf,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )

        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn(
            payload["error"]["code"],
            {"style_receipt_not_found", "style_receipt_directory_not_found"},
        )

    def test_stale_snapshot_conflict_preserves_new_prose_style(self) -> None:
        wf = Path(self.make(["T1: first"]))
        style_writer = np.load_record(wf)
        stale_writer = np.load_record(wf)
        style_writer["prose_style"] = nature_style.default_style_state()
        np.save_record(wf, style_writer)

        stale_writer["genre"] = "review"
        with self.assertRaises(np.NatureProgressError) as raised:
            np.save_record(wf, stale_writer)

        error = raised.exception
        self.assertEqual(error.code, "workflow_state_conflict")
        self.assertTrue(error.retryable)
        self.assertNotEqual(error.context["expected_etag"], error.context["actual_etag"])
        disk = read_state(str(wf))
        self.assertIn("prose_style", disk)
        self.assertIsNone(disk["genre"])

    def test_two_threads_from_one_snapshot_allow_only_one_save(self) -> None:
        wf = Path(self.make(["T1: first"]))
        records = [np.load_record(wf), np.load_record(wf)]
        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, str]] = []
        outcomes_lock = threading.Lock()

        def save(worker: str, record: dict) -> None:
            record["writer"] = worker
            barrier.wait(timeout=2)
            try:
                np.save_record(wf, record)
                outcome = ("saved", worker)
            except np.NatureProgressError as exc:
                outcome = (exc.code, worker)
            with outcomes_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=save, args=(f"worker-{index}", record))
            for index, record in enumerate(records, start=1)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(item[0] for item in outcomes), ["saved", "workflow_state_conflict"])
        winner = next(item[1] for item in outcomes if item[0] == "saved")
        self.assertEqual(read_state(str(wf))["writer"], winner)

    def test_two_processes_from_one_snapshot_allow_only_one_save(self) -> None:
        wf = Path(self.make(["T1: first"]))
        ready_dir = self.base / "ready"
        ready_dir.mkdir()
        worker_script = """
import json
import os
import time
from pathlib import Path
import nature_progress as np

workflow = Path(os.environ["NATURE_TEST_WORKFLOW"])
ready = Path(os.environ["NATURE_TEST_READY"])
worker = os.environ["NATURE_TEST_WORKER"]
record = np.load_record(workflow)
(ready / (worker + ".ready")).write_text("ready", encoding="utf-8")
deadline = time.monotonic() + 5
while len(list(ready.glob("*.ready"))) < 2 and time.monotonic() < deadline:
    time.sleep(0.01)
record["writer"] = worker
try:
    np.save_record(workflow, record)
    print(json.dumps({"result": "saved", "worker": worker}))
except np.NatureProgressError as exc:
    print(json.dumps({"result": exc.code, "worker": worker}))
"""
        processes: list[subprocess.Popen[str]] = []
        for worker in ("process-1", "process-2"):
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                [str(SCRIPT_DIR), env.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)
            env["NATURE_TEST_WORKFLOW"] = str(wf)
            env["NATURE_TEST_READY"] = str(ready_dir)
            env["NATURE_TEST_WORKER"] = worker
            processes.append(
                subprocess.Popen(
                    [sys.executable, "-c", worker_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env=env,
                )
            )

        outputs = [process.communicate(timeout=10) for process in processes]
        self.assertTrue(all(process.returncode == 0 for process in processes), outputs)
        payloads = [json.loads(stdout) for stdout, _ in outputs]
        self.assertEqual(
            sorted(payload["result"] for payload in payloads),
            ["saved", "workflow_state_conflict"],
        )
        winner = next(payload["worker"] for payload in payloads if payload["result"] == "saved")
        self.assertEqual(read_state(str(wf))["writer"], winner)

    def test_save_record_can_reuse_an_already_held_state_lock(self) -> None:
        wf = Path(self.make(["T1: first"]))
        with np.workflow_state_lock(wf):
            record = np.load_record(wf)
            record["genre"] = "review"
            np.save_record(wf, record, already_locked=True)

        self.assertEqual(read_state(str(wf))["genre"], "review")

    def test_repeated_save_record_timestamps_are_strictly_monotonic(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        timestamps = [record["updated_at"]]

        for _ in range(3):
            np.save_record(wf, record)
            timestamps.append(record["updated_at"])

        self.assertEqual(timestamps, sorted(set(timestamps)))

    def test_plain_dict_cannot_overwrite_existing_workflow_state(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = dict(np.load_record(wf))
        record["genre"] = "review"

        with self.assertRaises(np.NatureProgressError) as raised:
            np.save_record(wf, record)

        self.assertEqual(raised.exception.code, "workflow_state_snapshot_required")
        self.assertIsNone(read_state(str(wf))["genre"])

    def test_invalid_mirror_target_is_rejected_before_any_write(self) -> None:
        wf = Path(self.make(["T1: first"]))
        progress_path = wf / "progress.md"
        progress_path.unlink()
        progress_path.mkdir()
        before_state = (wf / "nature.yml").read_bytes()
        before_tasks = (wf / "tasks.md").read_bytes()
        record = np.load_record(wf)
        original_updated_at = record["updated_at"]
        record["genre"] = "review"

        with self.assertRaises(np.NatureProgressError) as raised:
            np.save_record(wf, record)

        self.assertEqual(raised.exception.code, "workflow_mirror_path_unsafe")
        self.assertEqual((wf / "nature.yml").read_bytes(), before_state)
        self.assertEqual((wf / "tasks.md").read_bytes(), before_tasks)
        self.assertTrue(progress_path.is_dir())
        self.assertEqual(record["updated_at"], original_updated_at)

    def test_state_cas_conflict_restores_mirrors_and_preserves_external_edit(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        record["genre"] = "review"
        before_progress = (wf / "progress.md").read_bytes()
        before_tasks = (wf / "tasks.md").read_bytes()
        original_replace = np.nature_atomic.atomic_replace_text
        external = dict(read_state(str(wf)))
        external["external_writer"] = True
        raced = False

        def replace_with_race(path: Path, text: str, **kwargs: object) -> None:
            nonlocal raced
            if Path(path).name == "nature.yml" and not raced:
                raced = True
                Path(path).write_text(
                    json.dumps(external, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                    newline="",
                )
            original_replace(path, text, **kwargs)

        with patch.object(np.nature_atomic, "atomic_replace_text", side_effect=replace_with_race):
            with self.assertRaises(np.NatureProgressError) as raised:
                np.save_record(wf, record)

        self.assertEqual(raised.exception.code, "workflow_state_conflict")
        self.assertTrue(read_state(str(wf))["external_writer"])
        self.assertIsNone(read_state(str(wf))["genre"])
        self.assertEqual((wf / "progress.md").read_bytes(), before_progress)
        self.assertEqual((wf / "tasks.md").read_bytes(), before_tasks)

    def test_runtime_mirror_write_failure_rolls_back_prior_mirror(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        record["genre"] = "review"
        record["tasks"][0]["title"] = "changed title"
        before = {
            name: (wf / name).read_bytes()
            for name in ("nature.yml", "progress.md", "tasks.md")
        }
        original_replace = np.nature_atomic.atomic_replace_text
        failed = False

        def replace_with_failure(path: Path, text: str, **kwargs: object) -> None:
            nonlocal failed
            if Path(path).name == "tasks.md" and not failed:
                failed = True
                raise PermissionError("forced tasks mirror failure")
            original_replace(path, text, **kwargs)

        with patch.object(np.nature_atomic, "atomic_replace_text", side_effect=replace_with_failure):
            with self.assertRaises(np.NatureProgressError) as raised:
                np.save_record(wf, record)

        self.assertEqual(raised.exception.code, "workflow_mirror_write_failed")
        for name, raw in before.items():
            self.assertEqual((wf / name).read_bytes(), raw)

    def test_keyboard_interrupt_rolls_back_prior_mirror(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        record["tasks"][0]["title"] = "changed title"
        before = {
            name: (wf / name).read_bytes()
            for name in ("nature.yml", "progress.md", "tasks.md")
        }
        original_replace = np.nature_atomic.atomic_replace_text

        def replace_with_interrupt(path: Path, text: str, **kwargs: object) -> None:
            if Path(path).name == "tasks.md":
                raise KeyboardInterrupt()
            original_replace(path, text, **kwargs)

        with patch.object(np.nature_atomic, "atomic_replace_text", side_effect=replace_with_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                np.save_record(wf, record)

        for name, raw in before.items():
            self.assertEqual((wf / name).read_bytes(), raw)

    def test_mirror_etag_is_rechecked_before_state_commit(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        record["external_state_only"] = True
        state_before = (wf / "nature.yml").read_bytes()
        progress_before = (wf / "progress.md").read_bytes()
        tasks_path = wf / "tasks.md"
        external_tasks = b"external tasks edit\n"
        original_snapshot = np._read_workflow_file_snapshot
        tasks_reads = 0

        def snapshot_with_race(path: Path, *, state_file: bool):
            nonlocal tasks_reads
            if Path(path) == tasks_path:
                tasks_reads += 1
                if tasks_reads == 2:
                    tasks_path.write_bytes(external_tasks)
            return original_snapshot(path, state_file=state_file)

        with patch.object(np, "_read_workflow_file_snapshot", side_effect=snapshot_with_race):
            with self.assertRaises(np.NatureProgressError) as raised:
                np.save_record(wf, record)

        self.assertEqual(raised.exception.code, "workflow_mirror_conflict")
        self.assertEqual((wf / "nature.yml").read_bytes(), state_before)
        self.assertEqual((wf / "progress.md").read_bytes(), progress_before)
        self.assertEqual(tasks_path.read_bytes(), external_tasks)

    def test_already_locked_requires_current_thread_to_hold_lock(self) -> None:
        wf = Path(self.make(["T1: first"]))
        record = np.load_record(wf)
        record["genre"] = "review"

        with self.assertRaises(np.NatureProgressError) as raised:
            np.save_record(wf, record, already_locked=True)

        self.assertEqual(raised.exception.code, "workflow_state_lock_required")
        self.assertFalse(raised.exception.retryable)
        self.assertIsNone(read_state(str(wf))["genre"])

    def test_workflow_state_lock_rejects_non_finite_timeout_structurally(self) -> None:
        wf = Path(self.make(["T1: first"]))
        for timeout in (float("nan"), float("inf"), 1e100):
            with self.subTest(timeout=timeout):
                with self.assertRaises(np.NatureProgressError) as raised:
                    with np.workflow_state_lock(wf, timeout=timeout):
                        self.fail("invalid timeout unexpectedly acquired a lock")
                self.assertEqual(
                    raised.exception.code,
                    "workflow_state_lock_timeout_invalid",
                )
                self.assertFalse(raised.exception.retryable)

    def test_workflow_state_lock_timeout_is_structured(self) -> None:
        wf = Path(self.make(["T1: first"]))
        ready = threading.Event()
        release = threading.Event()

        def hold_lock() -> None:
            with np.workflow_state_lock(wf):
                ready.set()
                release.wait(timeout=2)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        self.assertTrue(ready.wait(timeout=2))
        try:
            with self.assertRaises(np.NatureProgressError) as raised:
                with np.workflow_state_lock(wf, timeout=0.05):
                    self.fail("contended lock unexpectedly acquired")
        finally:
            release.set()
            holder.join(timeout=2)

        error = raised.exception
        self.assertEqual(error.code, "workflow_state_lock_timeout")
        self.assertTrue(error.retryable)
        self.assertEqual(error.context["lock_path"], str(wf / np.WORKFLOW_STATE_LOCK_FILE))

    def test_workflow_state_lock_detects_replaced_inode_on_exit(self) -> None:
        wf = Path(self.make(["T1: first"]))
        real_check = np._assert_open_lock_identity
        checks = 0

        def check_then_report_replacement(handle, lock_path: Path, workflow_dir: Path) -> None:
            nonlocal checks
            checks += 1
            if checks == 2:
                raise np.NatureProgressError(
                    "workflow state lock was replaced while it was held",
                    code="workflow_state_lock_replaced",
                    context={"lock_path": str(lock_path), "workflow_dir": str(workflow_dir)},
                )
            real_check(handle, lock_path, workflow_dir)

        with patch.object(np, "_assert_open_lock_identity", side_effect=check_then_report_replacement):
            with self.assertRaises(np.NatureProgressError) as raised:
                with np.workflow_state_lock(wf):
                    pass

        self.assertEqual(checks, 2)
        self.assertEqual(raised.exception.code, "workflow_state_lock_replaced")

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

    def test_legacy_workflow_without_profile_keeps_prose_completion_unchanged(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        np.command_start(None, wf, "draft", base=self.base)

        completed = np.command_complete(
            None, wf, "draft", "legacy evidence", base=self.base
        )

        disk = read_state(wf)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(disk["tasks"][0]["status"], "completed")
        self.assertNotIn("prose_style", disk)

    def test_profiled_prose_completion_without_receipt_fails_before_mutation(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        self.register_style_profile(wf)
        np.command_start(None, wf, "draft", base=self.base)
        output = self.base / "styled.md"
        output.write_text("Styled prose.\n", encoding="utf-8")
        before = read_state(wf)

        with self.assertRaises(np.NatureProgressError) as raised:
            np.command_complete(None, wf, "draft", "styled.md", base=self.base)

        self.assertIn(
            raised.exception.code,
            {"style_receipt_not_found", "style_receipt_directory_not_found"},
        )
        after = read_state(wf)
        self.assertEqual(after, before)
        self.assertEqual(after["tasks"][0]["status"], "active")
        self.assertEqual(after["active_task"], "draft")

    def test_profiled_prose_completion_accepts_real_audit_receipt(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        self.register_style_profile(wf)
        np.command_start(None, wf, "draft", base=self.base)
        output = self.base / "styled.md"
        output.write_text("Styled prose.\n", encoding="utf-8")
        resolved = nature_style.command_style_resolve(
            self.base, wf, section="discussion", task_id="draft"
        )
        audited = nature_style.command_style_audit(
            self.base,
            wf,
            "draft",
            output,
            section="discussion",
            profile_etag=resolved["profile_etag"],
            resolution_etag=resolved["resolution_etag"],
            operation="writing",
            style_checks="passed",
            content_invariants="passed",
        )

        completed = np.command_complete(
            None,
            wf,
            "draft",
            "styled.md",
            style_receipt=audited["receipt_path"],
            base=self.base,
        )

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(read_state(wf)["tasks"][0]["status"], "completed")

    def test_profiled_completion_rechecks_guard_before_commit(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        self.register_style_profile(wf)
        output = self.base / "styled.md"
        output.write_text("Styled prose.\n", encoding="utf-8")
        before = read_state(wf)
        stale = np.NatureProgressError(
            "receipt changed before commit",
            code="prose_style_receipt_stale",
        )

        with patch.object(
            nature_style,
            "assert_style_completion_allowed",
            side_effect=[None, stale],
        ) as guard:
            with self.assertRaises(np.NatureProgressError) as raised:
                np.command_complete(
                    None,
                    wf,
                    "draft",
                    output.name,
                    base=self.base,
                )

        self.assertEqual(raised.exception.code, "prose_style_receipt_stale")
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(read_state(wf), before)

    def test_profiled_completion_rolls_back_when_post_commit_guard_fails(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        self.register_style_profile(wf)
        output = self.base / "styled.md"
        output.write_text("Styled prose.\n", encoding="utf-8")
        stale = np.NatureProgressError(
            "receipt changed during commit",
            code="prose_style_receipt_stale",
        )

        with patch.object(
            nature_style,
            "assert_style_completion_allowed",
            side_effect=[None, None, stale],
        ) as guard:
            with self.assertRaises(np.NatureProgressError) as raised:
                np.command_complete(
                    None,
                    wf,
                    "draft",
                    output.name,
                    base=self.base,
                )

        self.assertEqual(raised.exception.code, "prose_style_receipt_stale")
        self.assertEqual(guard.call_count, 3)
        record = read_state(wf)
        self.assertEqual(record["tasks"][0]["status"], "pending")
        self.assertIsNone(record["tasks"][0]["completed_at"])

    def test_profiled_non_prose_task_completes_without_receipt(self) -> None:
        wf = self.make(["T1: Collect source metadata"])
        self.register_style_profile(wf)
        np.command_start(None, wf, "T1", base=self.base)

        completed = np.command_complete(
            None, wf, "T1", "metadata ledger", base=self.base
        )

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(read_state(wf)["tasks"][0]["status"], "completed")

    def test_complete_with_memory_review_cannot_bypass_style_guard(self) -> None:
        wf = self.make(["draft: Draft manuscript prose"])
        self.register_style_profile(wf)
        np.command_start(None, wf, "draft", base=self.base)
        output = self.base / "styled.md"
        output.write_text("Styled prose.\n", encoding="utf-8")
        before = read_state(wf)

        with self.assertRaises(np.NatureProgressError) as raised:
            nc.complete_with_memory_review(
                None,
                wf,
                "draft",
                "styled.md",
                project_root=self.base,
            )

        self.assertIn(
            raised.exception.code,
            {"style_receipt_not_found", "style_receipt_directory_not_found"},
        )
        self.assertEqual(read_state(wf), before)

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

    def test_facade_rejects_non_string_optional_arguments(self) -> None:
        wf = self.make(["T1: collect evidence"])
        with self.assertRaises(np.NatureProgressError) as query_error:
            nc.resume_with_memory(project_root=self.base, workflow_dir=wf, query=123)  # type: ignore[arg-type]
        self.assertEqual(query_error.exception.code, "invalid_query")

        with self.assertRaises(np.NatureProgressError) as notes_error:
            nc.complete_with_memory_review(
                None,
                wf,
                "T1",
                "evidence",
                notes=123,  # type: ignore[arg-type]
                project_root=self.base,
            )
        self.assertEqual(notes_error.exception.code, "invalid_notes")

    def test_block_review_keeps_json_safe_response_after_unexpected_review_failure(self) -> None:
        wf = self.make(["T1: block"])
        with patch.object(nc, "_review_after_progress", side_effect=KeyError("review unavailable")):
            result = nc.block_with_memory_review(
                None,
                wf,
                "T1",
                "waiting for source",
                project_root=self.base,
            )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["progress_committed"])
        self.assertEqual(result["memory_review"]["error"]["code"], "memory_review_internal_error")
        self.assertEqual(read_state(wf)["tasks"][0]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
