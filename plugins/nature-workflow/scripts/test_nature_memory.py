#!/usr/bin/env python3
"""Tests for Nature workflow project memory."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "nature_memory.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory  # noqa: E402


def valid_entry(entry_id: int = 1, title: str = "引用风格", body: str = "RIS 导出, EndNote 兼容。") -> str:
    return f"## M{entry_id} · {title}\n<!-- updated: 2026-06-20T12:00:00Z -->\n{body}\n"


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
        self.assertEqual(entries[0].entry_id, "M1")
        self.assertEqual(entries[0].title, "引用风格")
        self.assertEqual(entries[0].updated, "2026-06-20T12:00:00Z")
        self.assertEqual(entries[0].line, 1)

    def test_parse_multiple_entries(self) -> None:
        entries = nature_memory.parse_memory(valid_entry(1) + "\n" + valid_entry(2, "数据仓库"))

        self.assertEqual([entry.entry_id for entry in entries], ["M1", "M2"])
        self.assertEqual(entries[1].line, 5)

    def test_check_passes_valid_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(valid_entry(), encoding="utf-8")

            result = nature_memory.command_memory_check(base=repo)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["violations"], [])

    def assert_check_rule(self, text: str, rule: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(text, encoding="utf-8")

            result = nature_memory.command_memory_check(base=repo)

            self.assertFalse(result["ok"], result)
            self.assertIn(rule, {violation["rule"] for violation in result["violations"]})

    def test_check_rejects_body_over_char_limit(self) -> None:
        self.assert_check_rule(valid_entry(body="x" * 281), "body_chars")

    def test_check_rejects_body_over_line_limit(self) -> None:
        self.assert_check_rule(valid_entry(body="1\n2\n3\n4\n5"), "body_lines")

    def test_check_rejects_entry_count_over_limit(self) -> None:
        text = "\n".join(valid_entry(index, f"标题{index}") for index in range(1, 14))

        self.assert_check_rule(text, "max_entries")

    def test_check_rejects_title_over_limit(self) -> None:
        self.assert_check_rule(valid_entry(title="一" * 41), "title_length")

    def test_check_rejects_duplicate_id(self) -> None:
        self.assert_check_rule(valid_entry(1) + "\n" + valid_entry(1, "另一条"), "duplicate_id")

    def test_check_rejects_missing_timestamp(self) -> None:
        self.assert_check_rule("## M1 · 引用风格\nRIS 导出。\n", "timestamp_missing")

    def test_check_rejects_invalid_timestamp(self) -> None:
        self.assert_check_rule("## M1 · 引用风格\n<!-- updated: not-a-date -->\nRIS 导出。\n", "timestamp_invalid")

    def test_check_rejects_placeholder_timestamp(self) -> None:
        self.assert_check_rule("## M1 · 引用风格\n<!-- updated: YYYY-MM-DDTHH:MM:SSZ -->\nRIS 导出。\n", "timestamp_placeholder")

    def test_check_rejects_bad_title_format(self) -> None:
        self.assert_check_rule("# M1 引用风格\n<!-- updated: 2026-06-20T12:00:00Z -->\nRIS 导出。\n", "title_format")

    def test_touch_refreshes_or_inserts_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## M1 · 引用风格\n<!-- updated: 2000-01-01T00:00:00Z -->\nRIS 导出。\n",
                encoding="utf-8",
            )

            result = nature_memory.command_memory_touch(None, None, "M1", base=repo)
            text = (workflow / "memory.md").read_text(encoding="utf-8")
            entries = nature_memory.parse_memory(text)

            self.assertTrue(result["ok"])
            self.assertNotIn("2000-01-01T00:00:00Z", text)
            self.assertIsNotNone(entries[0].updated)
            parsed = datetime.fromisoformat(entries[0].updated.replace("Z", "+00:00"))
            self.assertEqual(parsed.tzinfo, timezone.utc)

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
            self.assertIn("[wf](docs/nature-workflows/wf/memory.md): 1 entry; M1 引用风格.", text)
            self.assertNotIn("\nold\n", text)

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

    def test_index_can_limit_to_one_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = make_workflow(repo, "first")
            second = make_workflow(repo, "second")
            (first / "memory.md").write_text(valid_entry(1, "第一篇"), encoding="utf-8")
            (second / "memory.md").write_text(valid_entry(1, "第二篇"), encoding="utf-8")

            result = nature_memory.command_memory_index("docs/nature-workflows", "first", base=repo, all_workflows=False)
            text = (repo / "AGENTS.md").read_text(encoding="utf-8")

            self.assertTrue(result["ok"], result)
            self.assertIn("[first](docs/nature-workflows/first/memory.md): 1 entry; M1 第一篇.", text)
            self.assertNotIn("second", text)

    def test_path_safety_rejects_workflow_outside_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            make_workflow(repo)

            with self.assertRaises(nature_memory.NatureProgressError):
                nature_memory.command_memory_check(workflow=str(repo / ".." / "outside"), base=repo)

    def test_cli_check_all_returns_two_for_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            workflow = make_workflow(repo)
            (workflow / "memory.md").write_text(
                "## M1 · 引用风格\n<!-- updated: TODO -->\nRIS 导出。\n",
                encoding="utf-8",
            )

            result = run_memory("check", "--all", "docs/nature-workflows", cwd=repo)
            payload = json.loads(result.stdout)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["violations"][0]["rule"], "timestamp_placeholder")

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


if __name__ == "__main__":
    unittest.main()
