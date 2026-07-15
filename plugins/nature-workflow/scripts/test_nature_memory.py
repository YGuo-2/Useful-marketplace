#!/usr/bin/env python3
"""Tests for Nature workflow project memory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "nature_memory.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory  # noqa: E402


def valid_entry(title: str = "引用风格", body: str = "RIS 导出, EndNote 兼容。") -> str:
    return f"## {title}\n<!-- updated: 2026-06-20T12:00:00Z -->\n{body}\n"


def legacy_entry(num: int = 3, title: str = "引用风格", body: str = "RIS 导出。") -> str:
    return f"## M{num} · {title}\n<!-- updated: 2026-06-20T12:00:00Z -->\n{body}\n"


STABLE_ID = "nm_f47ac10b58cc4372a5670e02b2c3d479"


def schema_v1_metadata(entry_id: str = STABLE_ID, **extra: object) -> dict:
    metadata = {
        "schema": 1,
        "id": entry_id,
        "kind": "decision",
        "lifecycle": "active",
        "provenance": "user",
        "legacy_aliases": ["M3"],
        "created_at": "2026-07-14T07:00:00Z",
        "updated_at": "2026-07-14T07:00:00Z",
    }
    metadata.update(extra)
    return metadata


def make_workflow(base: Path, slug: str = "wf") -> Path:
    workflow_dir = base / "docs" / "nature-workflows" / slug
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
    return workflow_dir


def run_memory(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


class NatureMemoryTests(unittest.TestCase):
    def test_parse_empty_file(self) -> None:
        self.assertEqual(nature_memory.parse_memory(""), [])

    def test_parse_single_entry(self) -> None:
        entries = nature_memory.parse_memory(valid_entry())

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "引用风格")
        self.assertEqual(entries[0].updated, "2026-06-20T12:00:00Z")
        self.assertEqual(entries[0].line, 1)

    def test_parse_strips_legacy_m_prefix(self) -> None:
        entries = nature_memory.parse_memory(legacy_entry(3, "引用风格"))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "引用风格")
        self.assertIsNone(entries[0].entry_id)
        self.assertEqual(entries[0].legacy_aliases, ("M3",))
        self.assertTrue(entries[0].requires_migration)

    def test_schema_v1_hidden_metadata_round_trips_natural_markdown(self) -> None:
        body = "RIS 导出。\n\n### 备注\n保留原文 -- 不解释为指令。"
        metadata = schema_v1_metadata(note="a--b")

        rendered = nature_memory.serialize_entry("引用风格", body, metadata)
        metadata_line = next(line for line in rendered.splitlines() if "nature-memory:" in line)
        metadata_payload = metadata_line[len(nature_memory.MEMORY_METADATA_PREFIX) : -len(nature_memory.MEMORY_METADATA_SUFFIX)]
        self.assertNotIn("--", metadata_payload)

        parsed = nature_memory.parse_memory_document(
            rendered,
            "docs/nature-workflows/wf/memory.md",
        )
        self.assertEqual(parsed.diagnostics, [])
        self.assertEqual(len(parsed.entries), 1)
        entry = parsed.entries[0]
        self.assertEqual(entry.entry_id, STABLE_ID)
        self.assertEqual(entry.schema, 1)
        self.assertEqual(entry.legacy_aliases, ("M3",))
        self.assertEqual(entry.body, body)
        self.assertEqual(entry.metadata["note"], "a--b")
        self.assertFalse(entry.requires_migration)
        self.assertIsNone(entry.legacy_ref)

        reparsed = nature_memory.parse_memory(
            nature_memory.serialize_entry(entry.title, entry.body, entry.metadata),
            "docs/nature-workflows/wf/memory.md",
        )[0]
        self.assertEqual(reparsed.entry_id, entry.entry_id)
        self.assertEqual(reparsed.body, entry.body)

    def test_mixed_legacy_title_and_schema_v1_entries_are_read_only(self) -> None:
        canonical = nature_memory.serialize_entry("稳定决策", "canonical body", schema_v1_metadata())
        text = legacy_entry(3, "旧别名") + "\n" + valid_entry("标题版", "legacy body") + "\n" + canonical

        parsed = nature_memory.parse_memory_document(text, "memory.md")

        self.assertEqual(parsed.diagnostics, [])
        self.assertEqual([entry.title for entry in parsed.entries], ["旧别名", "标题版", "稳定决策"])
        self.assertIsNone(parsed.entries[0].entry_id)
        self.assertEqual(parsed.entries[0].legacy_aliases, ("M3",))
        self.assertIsNone(parsed.entries[1].entry_id)
        self.assertEqual(parsed.entries[1].legacy_ref, "legacy:memory.md#L5:标题版")
        self.assertEqual(parsed.entries[2].entry_id, STABLE_ID)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            path = workflow / "memory.md"
            path.write_text(text, encoding="utf-8")
            before = path.read_bytes()

            result = nature_memory.command_memory_list(
                "docs/nature-workflows", "wf", base=repo
            )
            checked = nature_memory.command_memory_check(base=repo)

            self.assertTrue(result["ok"])
            self.assertTrue(checked["ok"], checked)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(result["workflows"][0]["entries"][1]["legacy_ref"], "legacy:" + str(path).replace("\\", "/") + "#L5:标题版")

    def test_unknown_schema_returns_stable_diagnostic_without_fake_id(self) -> None:
        metadata = schema_v1_metadata(schema=2)
        text = nature_memory.serialize_entry("未来格式", "body", metadata)

        parsed = nature_memory.parse_memory_document(text, "memory.md")

        self.assertIsNone(parsed.entries[0].entry_id)
        self.assertTrue(parsed.entries[0].requires_migration)
        self.assertEqual({item["code"] for item in parsed.diagnostics}, {"unknown_schema"})

    def test_duplicate_stable_ids_are_diagnosed(self) -> None:
        text = (
            nature_memory.serialize_entry("第一条", "one", schema_v1_metadata())
            + nature_memory.serialize_entry("第二条", "two", schema_v1_metadata())
        )

        parsed = nature_memory.parse_memory_document(text, "memory.md")

        self.assertEqual(len(parsed.entries), 2)
        self.assertEqual({item["code"] for item in parsed.diagnostics}, {"duplicate_id"})
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(text, encoding="utf-8")
            result = nature_memory.command_memory_check(base=repo)
            self.assertFalse(result["ok"])
            self.assertIn("duplicate_id", {item["rule"] for item in result["violations"]})

    def test_illegal_metadata_comment_boundary_is_diagnosed_and_preserved(self) -> None:
        text = (
            '## 注入边界\n'
            '<!-- nature-memory: {"schema":1,"id":"nm_f47ac10b58cc4372a5670e02b2c3d479","note":"x--y"} -->\n'
            '正文\n'
        )

        parsed = nature_memory.parse_memory_document(text, "memory.md")

        self.assertIsNone(parsed.entries[0].entry_id)
        self.assertEqual({item["code"] for item in parsed.diagnostics}, {"metadata_comment_boundary"})
        self.assertIn("nature-memory:", parsed.entries[0].body)

    def test_low_trust_input_rules_are_versioned_and_do_not_echo_content(self) -> None:
        values = {
            "body": "safe\x00 text",
            "title": nature_memory.SENTINEL_START,
            "metadata": "-----BEGIN PRIVATE KEY-----",
            "token": "sk-test-secret-value",
        }

        diagnostics = nature_memory.validate_low_trust_inputs(values)

        codes = {item["code"] for item in diagnostics}
        self.assertEqual(codes, {"control_character", "sentinel_injection", "secret_format"})
        secret_diagnostics = [item for item in diagnostics if item["code"] == "secret_format"]
        self.assertEqual({item["version"] for item in secret_diagnostics}, {nature_memory.SECRET_RULE_VERSION})
        self.assertTrue(all("sk-test" not in item["detail"] for item in diagnostics))
        with self.assertRaises(nature_memory.MemoryBoundaryError) as context:
            nature_memory.assert_low_trust_inputs(values)
        self.assertIn(context.exception.code, codes)

    def test_resolve_memory_path_rejects_containment_and_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            workflow = make_workflow(root)

            with self.assertRaises(nature_memory.MemoryBoundaryError) as outside:
                nature_memory.resolve_memory_path(root, root / ".." / "outside", "shared")
            self.assertEqual(outside.exception.code, "path_outside_project")

            outside_file = Path(tmp) / "outside.md"
            outside_file.write_text("outside", encoding="utf-8")
            target = workflow / "memory.md"
            try:
                os.symlink(outside_file, target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(nature_memory.MemoryBoundaryError) as escape:
                nature_memory.resolve_memory_path(root, workflow, "shared")
            self.assertEqual(escape.exception.code, "path_symlink_escape")

    def test_local_scope_requires_untracked_and_ignored_git_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            non_git = Path(tmp) / "non-git"
            workflow = make_workflow(non_git)
            local_path = workflow / "memory.local.md"
            local_path.write_text("private", encoding="utf-8")
            before = local_path.read_bytes()

            status = nature_memory.check_local_scope(non_git, local_path)

            self.assertFalse(status["ok"])
            self.assertEqual(status["code"], "local_scope_not_repository")
            self.assertEqual(local_path.read_bytes(), before)

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            subprocess.run(["git", "init", str(repo)], capture_output=True, text=True, check=True)
            ignore = repo / ".gitignore"
            ignore.write_text("docs/nature-workflows/*/memory.local.md\n", encoding="utf-8")
            local_path = workflow / "memory.local.md"
            protected = nature_memory.check_local_scope(repo, local_path)
            self.assertTrue(protected["ok"], protected)
            self.assertEqual(protected["code"], "local_scope_protected")

            local_path.write_text("private", encoding="utf-8")
            tracked = subprocess.run(
                ["git", "-C", str(repo), "add", "-f", str(local_path.relative_to(repo))],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(tracked.returncode, 0)
            status = nature_memory.check_local_scope(repo, local_path)
            self.assertFalse(status["ok"])
            self.assertEqual(status["code"], "local_scope_tracked")

    def test_unignored_local_is_rejected_and_default_shared_list_stays_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            subprocess.run(["git", "init", str(repo)], capture_output=True, text=True, check=True)
            local_path = workflow / "memory.local.md"
            local_path.write_text("## secret title\nprivate body\n", encoding="utf-8")
            status = nature_memory.check_local_scope(repo, local_path)
            self.assertFalse(status["ok"])
            self.assertEqual(status["code"], "local_scope_not_ignored")

            (workflow / "memory.md").write_text(valid_entry("shared title"), encoding="utf-8")
            result = nature_memory.command_memory_list(base=repo)
            serialized = json.dumps(result, ensure_ascii=False)
            self.assertIn("shared title", serialized)
            self.assertNotIn("secret title", serialized)
            self.assertNotIn("private body", serialized)

    def test_remember_create_replay_update_and_title_change_preserve_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            metadata = {"kind": "decision", "provenance": "user"}

            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "初始标题", "初始正文", metadata
            )
            self.assertTrue(created["ok"], created)
            self.assertEqual(created["operation"], "created")
            self.assertRegex(created["entry_id"], r"^nm_[0-9a-f]{32}$")
            first_bytes = (workflow / "memory.md").read_bytes()

            replay = nature_memory.command_memory_remember(
                repo, workflow, "shared", "初始标题", "初始正文", metadata
            )
            self.assertTrue(replay["ok"], replay)
            self.assertEqual(replay["operation"], "noop")
            self.assertEqual(replay["entry_id"], created["entry_id"])
            self.assertEqual((workflow / "memory.md").read_bytes(), first_bytes)

            updated = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "改名后的标题",
                "更新后的正文",
                metadata,
                entry_id=created["entry_id"],
                expected_etag=created["etag"],
            )
            self.assertTrue(updated["ok"], updated)
            self.assertEqual(updated["operation"], "updated")
            self.assertEqual(updated["entry_id"], created["entry_id"])
            entries = nature_memory.parse_memory((workflow / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual(entries[0].title, "改名后的标题")
            self.assertEqual(entries[0].entry_id, created["entry_id"])
            self.assertEqual(entries[0].body, "更新后的正文")
            self.assertNotEqual(updated["etag"], created["etag"])

    def test_remember_rejects_missing_or_stale_entry_etag_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            metadata = {"kind": "decision", "provenance": "user"}
            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "标题", "正文", metadata
            )
            path = workflow / "memory.md"
            before = path.read_bytes()

            missing = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "标题",
                "另一个正文",
                metadata,
                entry_id=created["entry_id"],
            )
            self.assertFalse(missing["ok"])
            self.assertEqual(missing["error"]["code"], "etag_required")
            self.assertEqual(path.read_bytes(), before)

            stale = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "标题",
                "另一个正文",
                metadata,
                entry_id=created["entry_id"],
                expected_etag="0" * 64,
            )
            self.assertFalse(stale["ok"])
            self.assertEqual(stale["error"]["code"], "etag_conflict")
            self.assertEqual(path.read_bytes(), before)

            unknown = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "标题",
                "另一个正文",
                metadata,
                entry_id="nm_00000000000040008000000000000000",
                expected_etag=created["etag"],
            )
            self.assertFalse(unknown["ok"])
            self.assertEqual(unknown["error"]["code"], "not_found")
            self.assertEqual(path.read_bytes(), before)

    def test_remember_rejects_external_file_change_before_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            path = workflow / "memory.md"
            original = nature_memory._replace_if_snapshot_matches

            def tamper_then_replace(target: Path, text: str, snapshot_etag: str) -> None:
                target.write_text("external complete file\n", encoding="utf-8")
                original(target, text, snapshot_etag)

            nature_memory._replace_if_snapshot_matches = tamper_then_replace
            try:
                result = nature_memory.command_memory_remember(
                    repo, workflow, "shared", "标题", "正文", {"kind": "decision"}
                )
            finally:
                nature_memory._replace_if_snapshot_matches = original

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "file_changed_outside_lock")
            self.assertEqual(path.read_text(encoding="utf-8"), "external complete file\n")

    def test_workflow_lock_timeout_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            path = workflow / "memory.md"
            with nature_memory.workflow_memory_lock(workflow, timeout=1.0):
                result = nature_memory.command_memory_remember(
                    repo,
                    workflow,
                    "shared",
                    "标题",
                    "正文",
                    {"kind": "decision"},
                    lock_timeout=0.05,
                )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "lock_timeout")
            self.assertTrue(result["error"]["retryable"])
            self.assertFalse(path.exists())

    def test_different_workflows_can_write_in_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")

            def remember(workflow: Path, title: str) -> dict:
                return nature_memory.command_memory_remember(
                    repo, workflow, "shared", title, "正文", {"kind": "decision"}
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda args: remember(*args), [(first, "第一篇"), (second, "第二篇")]))

            self.assertTrue(all(result["ok"] for result in results), results)
            self.assertEqual(nature_memory.parse_memory((first / "memory.md").read_text(encoding="utf-8"))[0].title, "第一篇")
            self.assertEqual(nature_memory.parse_memory((second / "memory.md").read_text(encoding="utf-8"))[0].title, "第二篇")

    def test_forget_archives_active_entry_and_preserves_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "待归档", "保留审计正文", {"kind": "decision"}
            )
            result = nature_memory.command_memory_forget(
                repo,
                workflow,
                "shared",
                created["entry_id"],
                created["etag"],
                "已被新证据替代",
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["operation"], "archived")
            shown = nature_memory.command_memory_show(repo, workflow, "shared", created["entry_id"])
            self.assertTrue(shown["ok"], shown)
            self.assertEqual(shown["entry"]["lifecycle"], "archived")
            self.assertEqual(shown["entry"]["body"], "保留审计正文")
            self.assertEqual(shown["entry"]["metadata"]["archive_reason"], "已被新证据替代")

            second = nature_memory.command_memory_forget(
                repo,
                workflow,
                "shared",
                created["entry_id"],
                result["etag"],
                "重复归档",
            )
            self.assertFalse(second["ok"])
            self.assertEqual(second["error"]["code"], "invalid_lifecycle_transition")

    def test_supersede_is_single_file_transaction_and_show_derives_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            source = nature_memory.command_memory_remember(
                repo, workflow, "shared", "旧决策", "旧正文", {"kind": "decision"}
            )
            result = nature_memory.command_memory_supersede(
                repo,
                workflow,
                "shared",
                source["entry_id"],
                source["etag"],
                "新决策",
                "新正文",
                {"kind": "decision", "provenance": "user"},
            )

            self.assertTrue(result["ok"], result)
            self.assertNotEqual(result["entry_id"], source["entry_id"])
            entries = nature_memory.parse_memory((workflow / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 2)
            old = next(entry for entry in entries if entry.entry_id == source["entry_id"])
            new = next(entry for entry in entries if entry.entry_id == result["entry_id"])
            self.assertEqual(old.metadata["lifecycle"], "superseded")
            self.assertEqual(new.metadata["lifecycle"], "active")
            self.assertEqual(new.metadata["supersedes"], [source["entry_id"]])

            shown = nature_memory.command_memory_show(repo, workflow, "shared", source["entry_id"])
            self.assertTrue(shown["ok"], shown)
            self.assertEqual(shown["entry"]["derived_successor_ids"], [result["entry_id"]])
            self.assertEqual(shown["entry"]["locator"], source["locator"])

            update = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "不应更新",
                "不应写入",
                {"kind": "decision"},
                entry_id=source["entry_id"],
                expected_etag=shown["entry"]["etag"],
            )
            self.assertFalse(update["ok"])
            self.assertEqual(update["error"]["code"], "invalid_lifecycle_transition")

    def test_scope_cannot_be_embedded_in_entry_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            result = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "标题",
                "正文",
                {"kind": "decision", "scope": "local"},
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "scope_in_metadata")
            self.assertFalse((workflow / "memory.md").exists())

    def test_remember_soft_budget_allows_write_and_returns_consolidation_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            results = []
            for index in range(13):
                results.append(
                    nature_memory.command_memory_remember(
                        repo,
                        workflow,
                        "shared",
                        f"预算条目{index}",
                        "短正文",
                        {"kind": "decision"},
                    )
                )

            self.assertTrue(all(result["ok"] for result in results), results)
            self.assertTrue(results[11]["budget"]["needs_consolidation"])
            self.assertTrue(results[12]["budget"]["needs_consolidation"])
            self.assertEqual(results[12]["budget"]["active_count"], 13)
            self.assertEqual(len(nature_memory.parse_memory((workflow / "memory.md").read_text(encoding="utf-8"))), 13)

    def test_remember_hard_file_budget_rejects_without_creating_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            result = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "超大正文",
                "x" * (nature_memory.HARD_FILE_BYTES + 1),
                {"kind": "decision"},
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "hard_file_budget")
            self.assertIn("manual backup", result["error"]["recovery"])
            self.assertFalse((workflow / "memory.md").exists())

    def test_supersedes_must_reference_same_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")
            source = nature_memory.command_memory_remember(
                repo, first, "shared", "source", "body", {"kind": "decision"}
            )
            result = nature_memory.command_memory_remember(
                repo,
                second,
                "shared",
                "cross-boundary",
                "body",
                {"kind": "decision", "supersedes": [source["entry_id"]]},
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "cross_boundary_supersedes")
            self.assertFalse((second / "memory.md").exists())

    def test_consolidate_plan_is_deterministic_and_apply_is_full_cas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            first = nature_memory.command_memory_remember(
                repo, workflow, "shared", "事实一", "正文一", {"kind": "decision"}
            )
            second = nature_memory.command_memory_remember(
                repo, workflow, "shared", "事实二", "正文二", {"kind": "decision"}
            )
            path = workflow / "memory.md"
            before_plan = path.read_bytes()
            plan = nature_memory.command_memory_consolidate_plan(
                repo,
                workflow,
                "shared",
                [first["entry_id"], second["entry_id"]],
            )
            reversed_plan = nature_memory.command_memory_consolidate_plan(
                repo,
                workflow,
                "shared",
                [second["entry_id"], first["entry_id"]],
            )
            self.assertTrue(plan["ok"], plan)
            self.assertEqual(plan["plan_id"], reversed_plan["plan_id"])
            self.assertEqual(path.read_bytes(), before_plan)
            self.assertFalse((workflow / ".nature-memory-plan").exists())

            applied = nature_memory.command_memory_consolidate_apply(
                repo,
                workflow,
                "shared",
                plan["plan_id"],
                plan["source_ids"],
                plan["source_etags"],
                "合并后的事实",
                "人工提供的合并正文",
                {"kind": "decision"},
            )
            self.assertTrue(applied["ok"], applied)
            entries = nature_memory.parse_memory(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 3)
            self.assertEqual(sum(entry.metadata["lifecycle"] == "active" for entry in entries), 1)
            successor = next(entry for entry in entries if entry.entry_id == applied["entry_id"])
            self.assertEqual(set(successor.metadata["supersedes"]), {first["entry_id"], second["entry_id"]})
            self.assertEqual(applied["budget"]["active_count"], 1)

    def test_consolidate_apply_rejects_stale_plan_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            first = nature_memory.command_memory_remember(
                repo, workflow, "shared", "事实一", "正文一", {"kind": "decision"}
            )
            second = nature_memory.command_memory_remember(
                repo, workflow, "shared", "事实二", "正文二", {"kind": "decision"}
            )
            plan = nature_memory.command_memory_consolidate_plan(
                repo, workflow, "shared", [first["entry_id"], second["entry_id"]]
            )
            changed = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "事实一改写",
                "正文一改写",
                {"kind": "decision"},
                entry_id=first["entry_id"],
                expected_etag=first["etag"],
            )
            self.assertTrue(changed["ok"], changed)
            before_apply = (workflow / "memory.md").read_bytes()
            stale = nature_memory.command_memory_consolidate_apply(
                repo,
                workflow,
                "shared",
                plan["plan_id"],
                plan["source_ids"],
                plan["source_etags"],
                "不应写入",
                "不应写入",
                {"kind": "decision"},
            )
            self.assertFalse(stale["ok"])
            self.assertEqual(stale["error"]["code"], "stale_plan")
            self.assertEqual((workflow / "memory.md").read_bytes(), before_apply)

    def test_migrate_dry_run_apply_preserves_legacy_alias_and_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            path = workflow / "memory.md"
            path.write_text(
                legacy_entry(3, "旧决策", "旧正文") + "\n" + valid_entry("重复标题", "重复正文"),
                encoding="utf-8",
            )
            before = path.read_bytes()

            dry_run = nature_memory.command_memory_migrate(repo, workflow, "shared", dry_run=True)

            self.assertTrue(dry_run["ok"], dry_run)
            self.assertEqual(dry_run["operation"], "dry_run")
            self.assertTrue(dry_run["can_apply"])
            self.assertEqual(len(dry_run["entries"]), 2)
            self.assertEqual(dry_run["entries"][0]["legacy_aliases"], ["M3"])
            self.assertTrue(all(entry["new_id"].startswith("nm_") for entry in dry_run["entries"]))
            self.assertNotEqual(dry_run["estimated_diff"]["bytes_before"], dry_run["estimated_diff"]["bytes_after"])
            self.assertEqual(path.read_bytes(), before)

            applied = nature_memory.command_memory_migrate(repo, workflow, "shared")

            self.assertTrue(applied["ok"], applied)
            self.assertEqual(applied["operation"], "migrated")
            self.assertTrue(applied["backup_path"])
            self.assertEqual(Path(applied["backup_path"]).read_bytes(), before)
            entries = nature_memory.parse_memory(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 2)
            self.assertTrue(all(entry.entry_id for entry in entries))
            migrated = next(entry for entry in entries if entry.title == "旧决策")
            self.assertEqual(migrated.legacy_aliases, ("M3",))
            self.assertEqual(migrated.metadata["legacy_updated_at"], "2026-06-20T12:00:00Z")
            self.assertFalse(any(entry.requires_migration for entry in entries))

            rerun = nature_memory.command_memory_migrate(repo, workflow, "shared")
            self.assertTrue(rerun["ok"], rerun)
            self.assertEqual(rerun["operation"], "noop")

    def test_migrate_duplicate_legacy_alias_is_hard_failure_without_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            path = workflow / "memory.md"
            path.write_text(legacy_entry(1, "第一条") + "\n" + legacy_entry(1, "第二条"), encoding="utf-8")
            before = path.read_bytes()

            dry_run = nature_memory.command_memory_migrate(repo, workflow, "shared", dry_run=True)
            self.assertTrue(dry_run["ok"], dry_run)
            self.assertFalse(dry_run["can_apply"])
            self.assertEqual(dry_run["collisions"][0]["alias"], "M1")

            applied = nature_memory.command_memory_migrate(repo, workflow, "shared")
            self.assertFalse(applied["ok"])
            self.assertEqual(applied["error"]["code"], "ambiguous_legacy_ref")
            self.assertEqual(applied["error"]["collisions"][0]["alias"], "M1")
            self.assertEqual(applied["error"]["scope"], "shared")
            self.assertIn("current_file_etag", applied["error"])
            self.assertEqual(path.read_bytes(), before)

    def test_local_migration_protects_backup_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
            (repo / ".gitignore").write_text("memory.local.md\n", encoding="utf-8")
            path = workflow / "memory.local.md"
            path.write_text("## M1 · local\nprivate\n", encoding="utf-8")
            result = nature_memory.command_memory_migrate(repo, workflow, "local")
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "local_backup_not_ignored")
            self.assertFalse((workflow / "memory.local.md.nature-memory.bak").exists())

    def test_migrate_all_is_per_workflow_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")
            (first / "memory.md").write_text(legacy_entry(1, "第一篇"), encoding="utf-8")
            canonical = nature_memory.command_memory_remember(
                repo, second, "shared", "第二篇", "canonical", {"kind": "decision"}
            )
            self.assertTrue(canonical["ok"], canonical)

            result = nature_memory.command_memory_migrate(repo, scope="shared", all_workflows=True)

            self.assertTrue(result["ok"], result)
            self.assertEqual(len(result["results"]), 2)
            operations = {Path(item["workflow_dir"]).name: item["operation"] for item in result["results"]}
            self.assertEqual(operations, {"first": "migrated", "second": "noop"})

    def test_parse_multiple_entries(self) -> None:
        entries = nature_memory.parse_memory(valid_entry("引用风格") + "\n" + valid_entry("数据仓库"))

        self.assertEqual([entry.title for entry in entries], ["引用风格", "数据仓库"])
        self.assertEqual(entries[1].line, 5)

    def test_body_may_contain_subheadings(self) -> None:
        # `###` and deeper are free-form body now, not entry boundaries.
        text = "## 引用风格\n<!-- updated: 2026-06-20T12:00:00Z -->\n### 细节\nRIS 导出。\n"
        entries = nature_memory.parse_memory(text)

        self.assertEqual(len(entries), 1)
        self.assertIn("### 细节", entries[0].body)

    def test_check_passes_valid_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")

            result = nature_memory.command_memory_check(base=repo)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["violations"], [])

    def _check(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(text, encoding="utf-8")
            return nature_memory.command_memory_check(base=repo)

    def assert_warns(self, text: str, rule: str) -> None:
        result = self._check(text)
        rules = {v["rule"] for v in result["violations"]}
        self.assertIn(rule, rules, result)
        # Warnings are non-blocking: ok stays True.
        self.assertTrue(result["ok"], result)
        for v in result["violations"]:
            if v["rule"] == rule:
                self.assertEqual(v["severity"], "warning", v)

    def assert_errors(self, text: str, rule: str) -> None:
        result = self._check(text)
        rules = {v["rule"] for v in result["violations"]}
        self.assertIn(rule, rules, result)
        self.assertFalse(result["ok"], result)
        for v in result["violations"]:
            if v["rule"] == rule:
                self.assertEqual(v["severity"], "error", v)

    def test_check_warns_body_over_char_limit(self) -> None:
        self.assert_warns(valid_entry(body="x" * 281), "body_chars")

    def test_check_warns_body_over_line_limit(self) -> None:
        self.assert_warns(valid_entry(body="1\n2\n3\n4\n5"), "body_lines")

    def test_check_warns_entry_count_over_limit_without_rejecting_active_entry(self) -> None:
        text = "\n".join(valid_entry(f"标题{index}") for index in range(1, 14))

        self.assert_warns(text, "max_entries")

    def test_check_warns_title_over_limit(self) -> None:
        self.assert_warns(valid_entry(title="一" * 41), "title_length")

    def test_check_warns_duplicate_title(self) -> None:
        self.assert_warns(valid_entry("引用风格") + "\n" + valid_entry("引用风格"), "duplicate_title")

    def test_check_allows_missing_timestamp(self) -> None:
        result = self._check("## 引用风格\nRIS 导出。\n")

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["violations"], [])

    def test_check_warns_invalid_timestamp(self) -> None:
        self.assert_warns("## 引用风格\n<!-- updated: not-a-date -->\nRIS 导出。\n", "timestamp_invalid")

    def test_check_warns_placeholder_timestamp(self) -> None:
        self.assert_warns("## 引用风格\n<!-- updated: YYYY-MM-DDTHH:MM:SSZ -->\nRIS 导出。\n", "timestamp_placeholder")

    def test_check_warns_empty_title_heading(self) -> None:
        self.assert_warns("## \n<!-- updated: 2026-06-20T12:00:00Z -->\nRIS 导出。\n", "empty_title")

    def test_touch_by_title_refreshes_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## 引用风格\n<!-- updated: 2000-01-01T00:00:00Z -->\nRIS 导出。\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_touch(None, None, "引用风格", base=repo)
            text = (workflow / "memory.md").read_text(encoding="utf-8")
            entries = nature_memory.parse_memory(text)

            self.assertTrue(result["ok"])
            self.assertEqual(result["entry"], "引用风格")
            self.assertNotIn("2000-01-01T00:00:00Z", text)
            self.assertIsNotNone(entries[0].updated)
            parsed = datetime.fromisoformat(entries[0].updated.replace("Z", "+00:00"))
            self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_touch_by_title_finds_legacy_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## M1 · 引用风格\n<!-- updated: 2000-01-01T00:00:00Z -->\nRIS 导出。\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_touch(None, None, "引用风格", base=repo)
            text = (workflow / "memory.md").read_text(encoding="utf-8")

            self.assertTrue(result["ok"])
            self.assertNotIn("2000-01-01T00:00:00Z", text)

    def test_touch_by_stable_id_keeps_metadata_adjacent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "Canonical", "body", {"kind": "decision"}
            )
            result = nature_memory.command_memory_touch(None, None, created["entry_id"], base=repo)
            lines = (workflow / "memory.md").read_text(encoding="utf-8").splitlines()
            self.assertTrue(result["ok"], result)
            self.assertTrue(lines[1].startswith(nature_memory.MEMORY_METADATA_PREFIX))
            parsed = nature_memory.parse_memory("\n".join(lines) + "\n")[0]
            self.assertEqual(parsed.entry_id, created["entry_id"])
            self.assertEqual(parsed.metadata["updated_at"], result["updated"])
            self.assertTrue(result["deprecated"])

    def test_show_legacy_alias_returns_legacy_ref_without_fabricated_locator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text("## M3 · 旧决策\n旧正文\n", encoding="utf-8")
            result = nature_memory.command_memory_show(repo, workflow, "shared", "M3")
            self.assertTrue(result["ok"], result)
            self.assertIsNone(result["entry"]["id"])
            self.assertIsNone(result["entry"]["locator"])
            self.assertTrue(result["entry"]["legacy_ref"])
            self.assertTrue(result["deprecated"])

    def test_touch_unknown_title_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")

            with self.assertRaises(nature_memory.NatureProgressError):
                nature_memory.command_memory_touch(None, None, "不存在", base=repo)

    def test_index_rewrites_sentinel_and_preserves_outer_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")
            agents = repo / "AGENTS.md"
            agents.write_text(
                "before\n\n"
                f"{nature_memory.SENTINEL_START}\nold\n{nature_memory.SENTINEL_END}\n\n"
                "after\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_index(base=repo)
            text = agents.read_text(encoding="utf-8")

            self.assertTrue(result["ok"], result)
            self.assertIn("before", text)
            self.assertIn("after", text)
            self.assertIn(nature_memory.FIXED_AGENTS_SECTION, text)
            self.assertNotIn("引用风格", text)
            self.assertNotIn("\nold\n", text)
            self.assertTrue(result["backup_path"])
            self.assertTrue(Path(result["backup_path"]).exists())

    def test_index_creates_missing_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")
            agents = repo / "AGENTS.md"
            agents.write_text("# Agents\n", encoding="utf-8")

            nature_memory.command_memory_index(base=repo)
            text = agents.read_text(encoding="utf-8")

            self.assertIn("# Agents", text)
            self.assertIn(nature_memory.SENTINEL_START, text)
            self.assertIn(nature_memory.SENTINEL_END, text)
            self.assertNotIn("引用风格", text)

    def test_index_workflow_argument_remains_global_repair_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")
            (first / "memory.md").write_text(valid_entry("第一篇"), encoding="utf-8")
            (second / "memory.md").write_text(valid_entry("第二篇"), encoding="utf-8")

            result = nature_memory.command_memory_index("docs/nature-workflows", "first", base=repo, all_workflows=False)
            text = (repo / "AGENTS.md").read_text(encoding="utf-8")

            self.assertTrue(result["ok"], result)
            self.assertIn(nature_memory.FIXED_AGENTS_SECTION, text)
            self.assertEqual(len(result["indexed"]), 2)
            self.assertNotIn("第一篇", text)
            self.assertNotIn("第二篇", text)

    def test_index_warns_but_does_not_abort_on_malformed(self) -> None:
        # F4: a duplicate title must produce a warning, not a silent drop or abort.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                valid_entry("引用风格") + "\n" + valid_entry("引用风格"),
                encoding="utf-8",
            )

            result = nature_memory.command_memory_index(base=repo)
            text = (repo / "AGENTS.md").read_text(encoding="utf-8")

            self.assertTrue(result["ok"], result)
            self.assertIn("duplicate_title", {w["rule"] for w in result["warnings"]})
            self.assertIn(nature_memory.SENTINEL_START, text)
            self.assertNotIn("引用风格", text)

    def test_path_safety_rejects_workflow_outside_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            make_workflow(repo)

            with self.assertRaises(nature_memory.NatureProgressError):
                nature_memory.command_memory_check(workflow=str(repo / ".." / "outside"), base=repo)

    def test_cli_check_all_returns_zero_for_soft_active_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "\n".join(valid_entry(f"标题{index}") for index in range(1, 14)),
                encoding="utf-8",
            )

            result = run_memory("check", "--all", "docs/nature-workflows", cwd=repo)
            payload = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(payload["ok"])
            self.assertIn("max_entries", {v["rule"] for v in payload["violations"]})

    def test_cli_check_all_returns_zero_for_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## 引用风格\n<!-- updated: TODO -->\nRIS 导出。\n",
                encoding="utf-8",
            )

            result = run_memory("check", "--all", "docs/nature-workflows", cwd=repo)
            payload = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(payload["ok"])
            self.assertIn("timestamp_placeholder", {v["rule"] for v in payload["violations"]})

    def test_parse_ignores_heading_inside_code_fence(self) -> None:
        # A `## ` line inside a fenced code block is body, not a phantom entry.
        text = (
            "## 结构说明\n<!-- updated: 2026-06-20T12:00:00Z -->\n示例:\n```md\n## 方法\n```\n\n"
            "## 真方法\n<!-- updated: 2026-06-20T12:00:00Z -->\n正文\n"
        )
        entries = nature_memory.parse_memory(text)

        self.assertEqual([e.title for e in entries], ["结构说明", "真方法"])

    def test_touch_ignores_fenced_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## 方法\n<!-- updated: 2000-01-01T00:00:00Z -->\n示例:\n```md\n## 方法\n```\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_touch(None, None, "方法", base=repo)
            text = (workflow / "memory.md").read_text(encoding="utf-8")

            # The real entry (line 1) is stamped; the fenced ## 方法 is left intact.
            self.assertTrue(result["ok"])
            self.assertNotIn("2000-01-01T00:00:00Z", text)
            self.assertIn("```md\n## 方法\n```", text)

    def test_parse_extracts_indented_timestamp(self) -> None:
        # A valid stamp with leading whitespace must still be extracted, not dropped.
        entries = nature_memory.parse_memory("## 引用风格\n   <!-- updated: 2026-06-20T12:00:00Z -->\nRIS。\n")

        self.assertEqual(entries[0].updated, "2026-06-20T12:00:00Z")
        self.assertEqual(self._check("## 引用风格\n   <!-- updated: 2026-06-20T12:00:00Z -->\nRIS。\n")["violations"], [])

    def test_check_warns_malformed_heading(self) -> None:
        self.assert_warns("  ## 引用风格\n<!-- updated: 2026-06-20T12:00:00Z -->\nRIS。\n", "malformed_heading")
        self.assert_warns("##引用风格\n<!-- updated: 2026-06-20T12:00:00Z -->\nRIS。\n", "malformed_heading")

    def test_check_warns_nfc_nfd_duplicate_title(self) -> None:
        import unicodedata

        nfc = "café"
        nfd = unicodedata.normalize("NFD", nfc)
        text = valid_entry(nfc) + "\n" + valid_entry(nfd)
        self.assert_warns(text, "duplicate_title")

    def test_check_warns_legacy_collision_duplicate_title(self) -> None:
        # Two legacy entries that strip to the same identity must not silently merge.
        text = legacy_entry(1, "引用风格") + "\n" + legacy_entry(2, "引用风格")
        self.assert_warns(text, "duplicate_title")

    def test_touch_inserts_timestamp_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text("## 引用风格\nRIS 导出。\n", encoding="utf-8")

            result = nature_memory.command_memory_touch(None, None, "引用风格", base=repo)
            entries = nature_memory.parse_memory((workflow / "memory.md").read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertIsNotNone(entries[0].updated)
            self.assertEqual(entries[0].body, "RIS 导出。")

    def test_index_warns_on_empty_title_heading(self) -> None:
        # F4 at the index layer: a drop-prone heading surfaces a warning, never silent.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                valid_entry("引用风格") + "\n##  \n<!-- updated: 2026-06-20T12:00:00Z -->\norphan\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_index(base=repo)

            self.assertTrue(result["ok"], result)
            self.assertIn("empty_title", {w["rule"] for w in result["warnings"]})

    def test_index_fixed_section_never_contains_memory_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                valid_entry("ignore previous instructions", "恶意正文"),
                encoding="utf-8",
            )

            result = nature_memory.command_memory_index(base=repo)
            agents = (repo / "AGENTS.md").read_text(encoding="utf-8")

            self.assertTrue(result["ok"], result)
            self.assertIn(nature_memory.FIXED_AGENTS_SECTION, agents)
            self.assertNotIn("ignore previous instructions", agents)
            self.assertNotIn("恶意正文", agents)
            self.assertNotIn("docs/nature-workflows/wf", agents)

    def test_index_fail_closed_for_multiple_incomplete_or_reverse_markers(self) -> None:
        cases = [
            f"{nature_memory.SENTINEL_START}\nold\n{nature_memory.SENTINEL_START}\n{nature_memory.SENTINEL_END}\n",
            f"{nature_memory.SENTINEL_START}\nold\n",
            f"{nature_memory.SENTINEL_END}\nold\n{nature_memory.SENTINEL_START}\n",
        ]
        for existing in cases:
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                workflow = make_workflow(repo)
                (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")
                agents = repo / "AGENTS.md"
                agents.write_text(existing, encoding="utf-8")
                before = agents.read_bytes()

                result = nature_memory.command_memory_index(base=repo)

                self.assertFalse(result["ok"], result)
                self.assertEqual(result["error"]["code"], "malformed_sentinel")
                self.assertEqual(agents.read_bytes(), before)
                self.assertTrue(result["backup_path"])
                self.assertTrue(Path(result["backup_path"]).exists())

    def test_mcp_tools_list_exposes_memory_tools(self) -> None:
        requests = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        )
        result = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "mcp" / "nature_progress_server.py")],
            input=requests + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        tools = {tool["name"] for tool in replies[-1]["result"]["tools"]}

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nature_memory_check", tools)
        self.assertIn("nature_memory_touch", tools)
        self.assertIn("nature_memory_index", tools)
        self.assertIn("nature_memory_list", tools)

    def test_mcp_memory_check_call_uses_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")
            requests = "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "nature_memory_check",
                                "arguments": {"project_root": str(repo), "workflow_dir": "wf"},
                            },
                        }
                    ),
                ]
            )

            result = subprocess.run(
                [sys.executable, str(PLUGIN_ROOT / "mcp" / "nature_progress_server.py")],
                input=requests + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
            replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            payload = json.loads(replies[-1]["result"]["content"][0]["text"])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["checked"][0]["entries"], 1)

    def test_alias_and_title_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                legacy_entry(3, "旧决策") + "\n" + valid_entry("M3"), encoding="utf-8"
            )
            result = nature_memory.command_memory_show(repo, workflow, "shared", "M3")
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "ambiguous_legacy_ref")

    def test_show_ignores_unrelated_unknown_schema_for_valid_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            valid = nature_memory.command_memory_remember(
                repo, workflow, "shared", "valid", "body", {"kind": "decision"}
            )
            future = nature_memory.serialize_entry("future", "body", schema_v1_metadata(schema=2))
            (workflow / "memory.md").write_text(
                (workflow / "memory.md").read_text(encoding="utf-8") + future,
                encoding="utf-8",
            )
            result = nature_memory.command_memory_show(repo, workflow, "shared", valid["entry_id"])
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["entry"]["id"], valid["entry_id"])
            self.assertTrue(any(item["code"] == "unknown_schema" for item in result["diagnostics"]))

    def test_local_migration_rejects_existing_external_hardlink_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
            (repo / ".gitignore").write_text(
                "docs/nature-workflows/*/memory.local.md*\n", encoding="utf-8"
            )
            path = workflow / "memory.local.md"
            path.write_text(legacy_entry(1, "local"), encoding="utf-8")
            external = Path(tmp) / "external-backup-target"
            external.write_text("must remain unchanged", encoding="utf-8")
            backup = path.with_name(path.name + nature_memory.AGENTS_BACKUP_SUFFIX)
            try:
                os.link(external, backup)
            except OSError as exc:
                self.skipTest(f"hardlink unavailable: {exc}")
            result = nature_memory.command_memory_migrate(repo, workflow, "local")
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "local_backup_exists")
            self.assertEqual(external.read_text(encoding="utf-8"), "must remain unchanged")

    def test_directory_memory_path_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").mkdir()
            result = nature_memory.command_memory_check(base=repo)
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "memory_path_not_regular_file")

    def test_local_scope_success_and_git_failure_are_observable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
            (repo / ".gitignore").write_text(
                "docs/nature-workflows/*/memory.local.md\n", encoding="utf-8"
            )
            success = nature_memory.command_memory_remember(
                repo, workflow, "local", "private", "private body", {"kind": "decision"}
            )
            self.assertTrue(success["ok"], success)
            self.assertTrue((workflow / "memory.local.md").exists())
            self.assertFalse((workflow / "memory.md").exists())

            failure_repo = Path(tmp) / "failure"
            failure_workflow = make_workflow(failure_repo)
            failed_process = subprocess.CompletedProcess([], 2, "", "forced git failure")
            with patch.object(nature_memory.subprocess, "run", return_value=failed_process):
                failure = nature_memory.command_memory_remember(
                    failure_repo, failure_workflow, "local", "private", "body", {"kind": "decision"}
                )
            self.assertFalse(failure["ok"], failure)
            self.assertEqual(failure["error"]["code"], "local_scope_git_failed")
            self.assertFalse((failure_workflow / "memory.local.md").exists())

    def test_final_cas_preserves_external_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "same", "before", {"kind": "decision"}
            )
            original_read = nature_memory._read_snapshot
            calls = 0
            path = workflow / "memory.md"

            def raced_read(target: Path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    path.write_text("## external\nexternal rewrite\n", encoding="utf-8")
                return original_read(target)

            with patch.object(nature_memory, "_read_snapshot", side_effect=raced_read):
                result = nature_memory.command_memory_remember(
                    repo,
                    workflow,
                    "shared",
                    "updated",
                    "must not overwrite external",
                    {"kind": "decision"},
                    entry_id=created["entry_id"],
                    expected_etag=created["etag"],
                )
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["error"]["code"], "file_changed_outside_lock")
            self.assertIn("external rewrite", path.read_text(encoding="utf-8"))

    def test_remember_supersedes_transitions_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            source = nature_memory.command_memory_remember(
                repo, workflow, "shared", "source", "body", {"kind": "decision"}
            )
            result = nature_memory.command_memory_remember(
                repo,
                workflow,
                "shared",
                "successor",
                "new body",
                {"kind": "decision", "supersedes": [source["entry_id"]]},
            )
            self.assertTrue(result["ok"], result)
            entries = nature_memory.parse_memory((workflow / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual(
                next(entry for entry in entries if entry.entry_id == source["entry_id"]).metadata["lifecycle"],
                "superseded",
            )
            self.assertEqual(result["source_ids"], [source["entry_id"]])

    def test_locator_is_consumable_by_show_and_recall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            created = nature_memory.command_memory_remember(
                repo, workflow, "shared", "locator title", "locator body", {"kind": "decision"}
            )
            shown = nature_memory.command_memory_show(repo, workflow, "shared", created["locator"])
            recalled = nature_memory.command_memory_recall(repo, workflow, "shared", created["locator"])
            self.assertTrue(shown["ok"], shown)
            self.assertTrue(recalled["ok"], recalled)
            self.assertEqual(recalled["results"][0]["id"], created["entry_id"])

    def test_consolidate_rejects_singleton_and_hard_budget_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            one = nature_memory.command_memory_remember(
                repo, workflow, "shared", "one", "body", {"kind": "decision"}
            )
            singleton = nature_memory.command_memory_consolidate_plan(repo, workflow, "shared", [one["entry_id"]])
            self.assertFalse(singleton["ok"], singleton)
            self.assertEqual(singleton["error"]["code"], "source_ids_required")

            first = nature_memory.serialize_entry("first", "x" * 140000, schema_v1_metadata())
            second_id = "nm_1234567890ab4cde8f0123456789abcd"
            second = nature_memory.serialize_entry("second", "y" * 140000, schema_v1_metadata(second_id))
            (workflow / "memory.md").write_text(first + second, encoding="utf-8")
            plan = nature_memory.command_memory_consolidate_plan(
                repo, workflow, "shared", [STABLE_ID, second_id]
            )
            self.assertTrue(plan["ok"], plan)
            applied = nature_memory.command_memory_consolidate_apply(
                repo, workflow, "shared", plan["plan_id"], plan["source_ids"], plan["source_etags"],
                "combined", "body", {"kind": "decision"}
            )
            self.assertFalse(applied["ok"], applied)
            self.assertEqual(applied["error"]["code"], "hard_file_budget")

    def test_list_local_scope_and_all_workflows_directory_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.local.md").write_text(valid_entry("local"), encoding="utf-8")
            local = nature_memory.command_memory_list(base=repo, scope="local")
            self.assertTrue(local["ok"], local)
            self.assertEqual(local["scope"], "local")
            self.assertEqual(local["workflows"][0]["scope"], "local")

            malformed = make_workflow(repo, "malformed")
            (malformed / "memory.md").mkdir()
            listed = nature_memory.command_memory_list(base=repo, all_workflows=True)
            self.assertFalse(listed["ok"], listed)
            self.assertEqual(listed["error"]["code"], "memory_path_not_regular_file")

    def test_show_scopes_diagnostics_to_the_requested_entry_and_preserves_legacy_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            canonical = nature_memory.command_memory_remember(
                repo, workflow, "shared", "same title", "valid body", {"kind": "decision"}
            )
            future = nature_memory.serialize_entry("same title", "future body", schema_v1_metadata(schema=2))
            (workflow / "memory.md").write_text(
                (workflow / "memory.md").read_text(encoding="utf-8") + future,
                encoding="utf-8",
            )
            shown = nature_memory.command_memory_show(repo, workflow, "shared", canonical["entry_id"])
            self.assertTrue(shown["ok"], shown)
            self.assertTrue(any(item["code"] == "unknown_schema" for item in shown["diagnostics"]))

            legacy_workflow = make_workflow(repo, "legacy-show")
            (legacy_workflow / "memory.md").write_text(
                legacy_entry(3, "timestamped", "legacy body"), encoding="utf-8"
            )
            legacy = nature_memory.command_memory_show(repo, legacy_workflow, "shared", "M3")
            self.assertTrue(legacy["ok"], legacy)
            self.assertEqual(legacy["entry"]["updated"], "2026-06-20T12:00:00Z")

    def test_update_supersedes_sources_and_locator_is_workflow_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")
            source = nature_memory.command_memory_remember(repo, first, "shared", "source", "body", {"kind": "decision"})
            target = nature_memory.command_memory_remember(repo, first, "shared", "target", "body", {"kind": "decision"})
            updated = nature_memory.command_memory_remember(
                repo,
                first,
                "shared",
                "target renamed",
                "new body",
                {"kind": "decision", "supersedes": [source["entry_id"]]},
                entry_id=target["entry_id"],
                expected_etag=target["etag"],
            )
            self.assertTrue(updated["ok"], updated)
            self.assertEqual(updated["operation"], "superseded")
            parsed = nature_memory.parse_memory((first / "memory.md").read_text(encoding="utf-8"))
            self.assertEqual(next(item for item in parsed if item.entry_id == source["entry_id"]).metadata["lifecycle"], "superseded")
            other = nature_memory.command_memory_remember(repo, second, "shared", "other", "body", {"kind": "decision"})
            mismatch = nature_memory.command_memory_show(repo, second, "shared", updated["locator"])
            self.assertFalse(mismatch["ok"], mismatch)
            self.assertEqual(mismatch["error"]["code"], "locator_workflow_mismatch")
            self.assertNotEqual(other["entry_id"], updated["entry_id"])

    def test_budget_and_recovery_boundaries_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            active = nature_memory.command_memory_remember(repo, workflow, "shared", "active", "body", {"kind": "decision"})
            for index in range(12):
                item = nature_memory.command_memory_remember(repo, workflow, "shared", f"archived-{index}", "body", {"kind": "decision"})
                nature_memory.command_memory_forget(repo, workflow, "shared", item["entry_id"], item["etag"], "test")
            checked = nature_memory.command_memory_check(base=repo)
            self.assertNotIn("max_entries", {item["rule"] for item in checked["violations"]})
            singleton = nature_memory.command_memory_consolidate_apply(
                repo, workflow, "shared", "plan_missing", [active["entry_id"]], [active["etag"]],
                "combined", "body", {"kind": "decision"},
            )
            self.assertFalse(singleton["ok"], singleton)
            self.assertEqual(singleton["error"]["code"], "source_ids_required")

            soft_workflow = make_workflow(repo, "soft-bytes")
            (soft_workflow / "memory.md").write_text(
                nature_memory.serialize_entry("large", "x" * (nature_memory.SOFT_ACTIVE_BYTES + 20), schema_v1_metadata()),
                encoding="utf-8",
            )
            soft = nature_memory.command_memory_check(base=repo, workflow="soft-bytes")
            self.assertIn("soft_active_bytes", {item["rule"] for item in soft["violations"]})

    def test_recall_validates_empty_all_workflow_roots_and_compacts_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs" / "nature-workflows").mkdir(parents=True)
            invalid = nature_memory.command_memory_recall_all(
                repo, repo / "docs" / "nature-workflows", "shared", "missing", top_k=6
            )
            self.assertFalse(invalid["ok"], invalid)
            self.assertEqual(invalid["error"]["code"], "invalid_top_k")

            workflow = make_workflow(repo, "compact")
            created = nature_memory.command_memory_remember(repo, workflow, "shared", "compact hit", "x" * 3000, {"kind": "decision"})
            compact = nature_memory.command_memory_recall(repo, workflow, "shared", "compact hit", max_bytes=4096)
            self.assertTrue(compact["ok"], compact)
            self.assertTrue(compact["results"], compact)
            self.assertEqual(compact["results"][0]["id"], created["entry_id"])

    def test_etag_errors_include_repair_context_and_missing_root_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            created = nature_memory.command_memory_remember(repo, workflow, "shared", "etag", "body", {"kind": "decision"})
            stale = nature_memory.command_memory_remember(
                repo, workflow, "shared", "changed", "body", {"kind": "decision"},
                entry_id=created["entry_id"], expected_etag="0" * 64,
            )
            self.assertFalse(stale["ok"], stale)
            self.assertEqual(stale["error"]["code"], "etag_conflict")
            for field in ("workflow_dir", "scope", "entry_id", "repair", "current_file_etag", "current_entry_etag"):
                self.assertIn(field, stale["error"])
            missing = nature_memory.command_memory_recall(repo / "missing", workflow, "shared", "query")
            self.assertFalse(missing["ok"], missing)
            self.assertEqual(missing["error"]["code"], "project_root_not_found")

    def test_migration_rejects_alias_title_collision_and_recovers_after_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            collision = make_workflow(repo, "collision")
            (collision / "memory.md").write_text(
                legacy_entry(3, "legacy", "body") + "\n## M3\ncanonical body\n", encoding="utf-8"
            )
            dry_run = nature_memory.command_memory_migrate(repo, collision, "shared", dry_run=True)
            self.assertFalse(dry_run["can_apply"])
            self.assertEqual(dry_run["collisions"][0]["type"], "alias_title_collision")

            recover = make_workflow(repo, "recover")
            (recover / "memory.md").write_text(legacy_entry(4, "recover", "body"), encoding="utf-8")
            with patch.object(
                nature_memory,
                "_replace_if_snapshot_matches",
                side_effect=nature_memory.MemoryBoundaryError("replace_failed", "forced"),
            ):
                failed = nature_memory.command_memory_migrate(repo, recover, "shared")
            self.assertFalse(failed["ok"], failed)
            self.assertFalse((recover / "memory.md.nature-memory.bak").exists())
            retried = nature_memory.command_memory_migrate(repo, recover, "shared")
            self.assertTrue(retried["ok"], retried)

    def test_migrate_all_reports_invalid_workflow_and_processes_valid_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            valid = make_workflow(repo, "valid")
            (valid / "memory.md").write_text(legacy_entry(5, "valid", "body"), encoding="utf-8")
            invalid = make_workflow(repo, "invalid")
            (invalid / "memory.md").mkdir()
            result = nature_memory.command_memory_migrate(
                repo, scope="shared", all_workflows=True
            )
            self.assertFalse(result["ok"], result)
            self.assertTrue(any(item.get("operation") == "migrated" for item in result["results"]), result)
            self.assertTrue(any(item.get("error", {}).get("code") == "memory_path_not_regular_file" for item in result["results"]), result)


if __name__ == "__main__":
    unittest.main()
