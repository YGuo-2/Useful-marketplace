#!/usr/bin/env python3
"""Smoke test: the MCP server round-trips non-ASCII (Chinese) task titles.

Regression guard for the Windows failure where stdio defaults to a narrow
locale codec. We reproduce it cross-platform by forcing a narrow child codec
via ``PYTHONIOENCODING=ascii``; the server must still succeed because
``main()`` reconfigures its stdin/stdout to UTF-8.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1] / "mcp" / "nature_progress_server.py"


def _rpc(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _run_rpc(requests: list[dict]) -> dict[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input="\n".join(_rpc(request) for request in requests) + "\n",
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(f"MCP server failed: {proc.stderr}")
    return {
        reply["id"]: reply
        for line in proc.stdout.splitlines()
        if line.strip()
        for reply in [json.loads(line)]
        if reply.get("id") is not None
    }


def _tool_call(request_id: int, name: str, arguments: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def _legacy_memory(alias: int, title: str, body: str = "legacy body") -> str:
    return f"## M{alias} · {title}\n<!-- updated: 2026-06-20T12:00:00Z -->\n{body}\n"


class ServerEncodingSmokeTest(unittest.TestCase):
    def test_chinese_task_survives_narrow_child_codec(self) -> None:
        requests = "\n".join(
            [
                _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                _rpc(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "nature_new_workflow",
                            "arguments": {
                                "slug": "zh",
                                "title": "综述测试",
                                "tasks": ["search: 检索式生成与多源检索"],
                            },
                        },
                    }
                ),
            ]
        ) + "\n"

        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **os.environ,
                "PYTHONIOENCODING": "ascii",  # simulate a Windows narrow codec
                "NATURE_WORKFLOW_BASE_DIR": tmp,
            }
            proc = subprocess.run(
                [sys.executable, str(SERVER)],
                input=requests.encode("utf-8"),
                capture_output=True,
                env=env,
                timeout=30,
            )

        stderr = proc.stderr.decode("utf-8", "replace")
        out = proc.stdout.decode("utf-8")
        replies = [json.loads(line) for line in out.splitlines() if line.strip()]
        call_replies = [r for r in replies if r.get("id") == 2]
        self.assertTrue(call_replies, msg=f"no reply for the Chinese tools/call:\n{stderr}")
        self.assertNotIn("error", call_replies[0], msg=stderr)
        # the Chinese title round-tripped through both stdin and stdout
        self.assertIn("综述测试", out)

    def test_tools_list_keeps_legacy_and_exposes_memory_facade_tools(self) -> None:
        requests = "\n".join(
            [
                _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                _rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            ]
        ) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, timeout=30)
        replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        tools = {tool["name"] for tool in replies[-1]["result"]["tools"]}
        self.assertIn("nature_memory_check", tools)
        self.assertIn("nature_memory_touch", tools)
        self.assertIn("nature_memory_remember", tools)
        self.assertIn("nature_memory_recall", tools)
        self.assertIn("nature_resume_with_memory", tools)
        self.assertIn("nature_complete_with_memory_review", tools)
        self.assertIn("nature_block_with_memory_review", tools)

    def test_memory_read_schemas_require_explicit_workflow_selection(self) -> None:
        request = _rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}) + "\n"
        proc = subprocess.run([sys.executable, str(SERVER)], input=request, text=True, capture_output=True, timeout=30)
        replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        declared = {tool["name"]: tool["inputSchema"] for tool in replies[-1]["result"]["tools"]}
        for name in ("nature_memory_check", "nature_memory_list", "nature_memory_recall", "nature_memory_migrate"):
            condition = declared[name]["allOf"][0]
            self.assertIn("all_workflows", condition["if"]["required"])
            self.assertEqual(condition["if"]["properties"]["all_workflows"]["const"], True)
            self.assertEqual(condition["else"]["required"], ["workflow_dir"])

    def test_memory_dispatch_does_not_broaden_missing_workflow_and_validates_empty_all_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nature_memory_list", "arguments": {"project_root": tmp, "scope": "shared"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "nature_memory_recall", "arguments": {"project_root": tmp, "scope": "shared", "query": "empty", "all_workflows": True, "top_k": 6}}},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nature_memory_migrate", "arguments": {"project_root": tmp, "scope": "shared", "workflow_dir": "docs/nature-workflows/wf", "dry_run": True}}},
            ]
            proc = subprocess.run([sys.executable, str(SERVER)], input="\n".join(_rpc(item) for item in requests) + "\n", text=True, capture_output=True, timeout=30)
            replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
            missing_workflow = next(reply for reply in replies if reply.get("id") == 1)
            invalid_all_recall = next(reply for reply in replies if reply.get("id") == 2)
            migrate = next(reply for reply in replies if reply.get("id") == 3)
            self.assertIn("error", missing_workflow)
            self.assertIn("error", invalid_all_recall)
            self.assertNotIn("error", migrate)
            migrate_payload = json.loads(migrate["result"]["content"][0]["text"])
            self.assertEqual(migrate_payload["error"]["code"], "invalid_workflow_dir")

    def test_legacy_migration_round_trips_over_json_rpc_and_isolates_batch_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_root = root / "docs" / "nature-workflows"

            def make_workflow(slug: str) -> Path:
                workflow = workflow_root / slug
                workflow.mkdir(parents=True)
                (workflow / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
                return workflow

            single = make_workflow("single")
            single_path = single / "memory.md"
            single_path.write_text(_legacy_memory(3, "single legacy"), encoding="utf-8")
            single_before = single_path.read_bytes()

            dry_reply = _run_rpc(
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                    _tool_call(
                        2,
                        "nature_memory_migrate",
                        {"project_root": tmp, "workflow_dir": str(single), "scope": "shared", "dry_run": True},
                    ),
                ]
            )[2]
            dry = json.loads(dry_reply["result"]["content"][0]["text"])
            self.assertTrue(dry["ok"], dry)
            self.assertEqual(dry["operation"], "dry_run")
            self.assertTrue(dry["can_apply"])
            self.assertEqual(dry["entries"][0]["legacy_aliases"], ["M3"])
            self.assertNotEqual(dry["estimated_diff"]["bytes_before"], dry["estimated_diff"]["bytes_after"])
            self.assertEqual(single_path.read_bytes(), single_before)

            apply_reply = _run_rpc(
                [
                    {"jsonrpc": "2.0", "id": 3, "method": "initialize"},
                    _tool_call(
                        4,
                        "nature_memory_migrate",
                        {"project_root": tmp, "workflow_dir": str(single), "scope": "shared"},
                    ),
                ]
            )[4]
            applied = json.loads(apply_reply["result"]["content"][0]["text"])
            self.assertTrue(applied["ok"], applied)
            self.assertEqual(applied["operation"], "migrated")
            self.assertEqual(Path(applied["backup_path"]).read_bytes(), single_before)
            self.assertIn('"legacy_aliases":["M3"]', single_path.read_text(encoding="utf-8"))

            collision = make_workflow("collision")
            collision_path = collision / "memory.md"
            collision_path.write_text(_legacy_memory(4, "first") + "\n" + _legacy_memory(4, "second"), encoding="utf-8")
            collision_before = collision_path.read_bytes()
            collision_replies = _run_rpc(
                [
                    {"jsonrpc": "2.0", "id": 5, "method": "initialize"},
                    _tool_call(
                        6,
                        "nature_memory_migrate",
                        {"project_root": tmp, "workflow_dir": str(collision), "scope": "shared", "dry_run": True},
                    ),
                    _tool_call(
                        7,
                        "nature_memory_migrate",
                        {"project_root": tmp, "workflow_dir": str(collision), "scope": "shared"},
                    ),
                ]
            )
            collision_dry = json.loads(collision_replies[6]["result"]["content"][0]["text"])
            collision_apply = json.loads(collision_replies[7]["result"]["content"][0]["text"])
            self.assertTrue(collision_dry["ok"], collision_dry)
            self.assertFalse(collision_dry["can_apply"])
            self.assertEqual(collision_dry["collisions"][0]["alias"], "M4")
            self.assertFalse(collision_apply["ok"], collision_apply)
            self.assertEqual(collision_apply["error"]["code"], "ambiguous_legacy_ref")
            self.assertEqual(collision_path.read_bytes(), collision_before)

            batch_good = make_workflow("batch-good")
            batch_good_path = batch_good / "memory.md"
            batch_good_path.write_text(_legacy_memory(5, "batch good"), encoding="utf-8")
            batch_collision = make_workflow("batch-collision")
            batch_collision_path = batch_collision / "memory.md"
            batch_collision_path.write_text(
                _legacy_memory(6, "batch first") + "\n" + _legacy_memory(6, "batch second"),
                encoding="utf-8",
            )
            batch_collision_before = batch_collision_path.read_bytes()
            batch_reply = _run_rpc(
                [
                    {"jsonrpc": "2.0", "id": 8, "method": "initialize"},
                    _tool_call(
                        9,
                        "nature_memory_migrate",
                        {"project_root": tmp, "scope": "shared", "all_workflows": True},
                    ),
                ]
            )[9]
            batch = json.loads(batch_reply["result"]["content"][0]["text"])
            self.assertFalse(batch["ok"], batch)
            self.assertEqual(batch["operation"], "partial")
            results = {
                Path(item.get("workflow_dir") or item.get("error", {}).get("workflow_dir")).name: item
                for item in batch["results"]
            }
            self.assertEqual(results["batch-good"]["operation"], "migrated")
            self.assertFalse(results["batch-collision"]["ok"])
            self.assertEqual(results["batch-collision"]["error"]["code"], "ambiguous_legacy_ref")
            self.assertNotEqual(batch_good_path.read_bytes(), _legacy_memory(5, "batch good").encode("utf-8"))
            self.assertTrue((batch_good_path.with_name("memory.md.nature-memory.bak")).exists())
            self.assertEqual(batch_collision_path.read_bytes(), batch_collision_before)

    def test_facade_missing_project_root_returns_structured_project_root_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = [
                {"workflow_dir": "docs/nature-workflows/missing", "scope": "shared"},
                {"project_root": str(Path(tmp) / "does-not-exist"), "workflow_dir": "docs/nature-workflows/missing", "scope": "shared"},
            ]
            for request_id, arguments in enumerate(cases, start=1):
                reply = _run_rpc([_tool_call(request_id, "nature_resume_with_memory", arguments)])[request_id]
                self.assertEqual(reply["error"]["code"], -32000, reply)
                self.assertEqual(reply["error"]["data"]["code"], "project_root_not_found", reply)
                self.assertEqual(reply["error"]["data"]["detail"], "project_root must exist", reply)
                self.assertFalse(reply["error"]["data"]["retryable"], reply)

    def test_facade_schema_and_dispatch_enforce_context_bounds(self) -> None:
        listed = _run_rpc([{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}])[1]
        tools = {tool["name"]: tool for tool in listed["result"]["tools"]}
        for name in ("nature_resume_with_memory", "nature_complete_with_memory_review", "nature_block_with_memory_review"):
            properties = tools[name]["inputSchema"]["properties"]
            self.assertEqual(properties["top_k"]["minimum"], 1)
            self.assertEqual(properties["top_k"]["maximum"], 5)
            self.assertEqual(properties["max_bytes"]["minimum"], 256)
            self.assertEqual(properties["max_bytes"]["maximum"], 4096)

        with tempfile.TemporaryDirectory() as tmp:
            base = {"project_root": tmp, "workflow_dir": "docs/nature-workflows/missing", "scope": "shared"}
            cases = [
                ("nature_resume_with_memory", {**base, "top_k": 0}, "invalid_top_k"),
                ("nature_resume_with_memory", {**base, "max_bytes": 4097}, "invalid_max_bytes"),
                ("nature_complete_with_memory_review", {**base, "task_id": "T1", "evidence": "evidence", "top_k": True}, "invalid_top_k"),
                ("nature_complete_with_memory_review", {**base, "task_id": "T1", "evidence": "evidence", "max_bytes": 255}, "invalid_max_bytes"),
                ("nature_block_with_memory_review", {**base, "task_id": "T1", "reason": "reason", "top_k": 6}, "invalid_top_k"),
                ("nature_block_with_memory_review", {**base, "task_id": "T1", "reason": "reason", "max_bytes": 0}, "invalid_max_bytes"),
            ]
            requests = [_tool_call(index, name, arguments) for index, (name, arguments, _) in enumerate(cases, start=2)]
            replies = _run_rpc(requests)
            for request_id, (_, _, expected_code) in enumerate(cases, start=2):
                reply = replies[request_id]
                self.assertEqual(reply["error"]["code"], -32602, reply)
                self.assertEqual(reply["error"]["data"]["code"], expected_code, reply)
                self.assertFalse(reply["error"]["data"]["retryable"], reply)

    def test_required_string_and_scope_errors_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = {"project_root": tmp, "workflow_dir": "docs/nature-workflows/wf"}
            cases = [
                ({**base, "scope": "shared"}, "missing_query"),
                ({**base, "scope": "invalid", "query": "query"}, "invalid_scope"),
                ({**base, "scope": "shared", "query": 7}, "invalid_query"),
            ]
            requests = [
                _tool_call(index, "nature_memory_recall", arguments)
                for index, (arguments, _) in enumerate(cases, start=1)
            ]
            replies = _run_rpc(requests)
            for request_id, (_, expected_code) in enumerate(cases, start=1):
                reply = replies[request_id]
                self.assertEqual(reply["error"]["code"], -32602, reply)
                self.assertEqual(reply["error"]["data"]["code"], expected_code, reply)
                self.assertIn("detail", reply["error"]["data"], reply)
                self.assertFalse(reply["error"]["data"]["retryable"], reply)

    def test_new_memory_tools_round_trip_real_json_rpc_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            create_requests = "\n".join(
                [
                    _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                    _rpc(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "nature_new_workflow",
                                "arguments": {"project_root": tmp, "slug": "wf", "title": "Memory test", "tasks": ["T1: recall"]},
                            },
                        }
                    ),
                ]
            ) + "\n"
            create_proc = subprocess.run([sys.executable, str(SERVER)], input=create_requests, text=True, capture_output=True, timeout=30)
            create_replies = [json.loads(line) for line in create_proc.stdout.splitlines() if line.strip()]
            create_reply = next(reply for reply in create_replies if reply.get("id") == 2)
            create_payload = json.loads(create_reply["result"]["content"][0]["text"])
            workflow_dir = create_payload["workflow_dir"]

            requests = "\n".join(
                [
                    _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                    _rpc(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "nature_memory_remember",
                                "arguments": {
                                    "project_root": tmp,
                                    "workflow_dir": workflow_dir,
                                    "scope": "shared",
                                    "title": "MCP decision",
                                    "body": "remembered body",
                                    "metadata": {"kind": "decision", "provenance": "user"},
                                },
                            },
                        }
                    ),
                    _rpc(
                        {
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {
                                "name": "nature_memory_recall",
                                "arguments": {
                                    "project_root": tmp,
                                    "workflow_dir": workflow_dir,
                                    "scope": "shared",
                                    "query": "MCP decision",
                                },
                            },
                        }
                    ),
                ]
            ) + "\n"
            proc = subprocess.run([sys.executable, str(SERVER)], input=requests, text=True, capture_output=True, timeout=30)
            replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
            remember_reply = next(reply for reply in replies if reply.get("id") == 3)
            recall_reply = next(reply for reply in replies if reply.get("id") == 4)
            remember_payload = json.loads(remember_reply["result"]["content"][0]["text"])
            recall_payload = json.loads(recall_reply["result"]["content"][0]["text"])
            self.assertTrue(remember_payload["ok"], remember_payload)
            self.assertTrue(recall_payload["ok"], recall_payload)
            self.assertEqual(recall_payload["results"][0]["title"], "MCP decision")

            entry_id = remember_payload["entry_id"]
            entry_etag = remember_payload["etag"]
            lifecycle_requests = "\n".join(
                [
                    _rpc({"jsonrpc": "2.0", "id": 5, "method": "initialize"}),
                    _rpc({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "nature_memory_show", "arguments": {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "entry_id": entry_id}}}),
                    _rpc({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "nature_memory_forget", "arguments": {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "entry_id": entry_id, "expected_etag": entry_etag, "reason": "MCP lifecycle test"}}}),
                    _rpc({"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "nature_memory_recall", "arguments": {"project_root": tmp, "scope": "shared", "query": "MCP decision", "all_workflows": True}}}),
                ]
            ) + "\n"
            lifecycle_proc = subprocess.run([sys.executable, str(SERVER)], input=lifecycle_requests, text=True, capture_output=True, timeout=30)
            lifecycle_replies = [json.loads(line) for line in lifecycle_proc.stdout.splitlines() if line.strip()]
            show_payload = json.loads(next(reply for reply in lifecycle_replies if reply.get("id") == 6)["result"]["content"][0]["text"])
            forget_payload = json.loads(next(reply for reply in lifecycle_replies if reply.get("id") == 7)["result"]["content"][0]["text"])
            all_recall_payload = json.loads(next(reply for reply in lifecycle_replies if reply.get("id") == 8)["result"]["content"][0]["text"])
            self.assertTrue(show_payload["ok"], show_payload)
            self.assertTrue(forget_payload["ok"], forget_payload)
            self.assertTrue(all_recall_payload["ok"], all_recall_payload)
            self.assertTrue(all_recall_payload["all_workflows"])

    def test_all_declared_tools_round_trip_over_real_json_rpc(self) -> None:
        def rpc(request_id: int, name: str, arguments: dict | None = None) -> dict:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}]
            requests.append({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            requests.append(rpc(3, "nature_new_workflow", {"project_root": tmp, "slug": "wf", "title": "All tools", "tasks": ["T1: first", "T2: second"]}))
            requests.append(rpc(4, "nature_discover_workflows", {"project_root": tmp, "workflow_root": "docs/nature-workflows"}))

            # The remaining workflow_dir is filled after the first process reply
            # is known; run the bootstrap calls separately so every later call is
            # still a real JSON-RPC request.
            bootstrap = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            replies = [json.loads(line) for line in bootstrap.stdout.splitlines() if line.strip()]
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            listed = next(reply for reply in replies if reply.get("id") == 2)
            declared = {tool["name"] for tool in listed["result"]["tools"]}
            expected_names = {
                "nature_new_workflow", "nature_discover_workflows", "nature_status", "nature_resume",
                "nature_start_task", "nature_complete_task", "nature_block_task", "nature_log_note",
                "nature_spec", "nature_memory_check", "nature_memory_touch", "nature_memory_index",
                "nature_memory_list", "nature_memory_remember", "nature_memory_recall", "nature_memory_show",
                "nature_memory_forget", "nature_memory_supersede", "nature_memory_consolidate_plan",
                "nature_memory_consolidate_apply", "nature_memory_migrate", "nature_resume_with_memory",
                "nature_complete_with_memory_review", "nature_block_with_memory_review",
            }
            self.assertEqual(declared, expected_names)
            created = json.loads(next(reply for reply in replies if reply.get("id") == 3)["result"]["content"][0]["text"])
            workflow_dir = created["workflow_dir"]

            calls = [
                rpc(5, "nature_status", {"project_root": tmp, "workflow_dir": workflow_dir}),
                rpc(6, "nature_resume", {"project_root": tmp, "workflow_dir": workflow_dir}),
                rpc(7, "nature_start_task", {"project_root": tmp, "workflow_dir": workflow_dir, "task_id": "T1"}),
                rpc(8, "nature_complete_task", {"project_root": tmp, "workflow_dir": workflow_dir, "task_id": "T1", "evidence": "rpc evidence"}),
                rpc(9, "nature_start_task", {"project_root": tmp, "workflow_dir": workflow_dir, "task_id": "T2"}),
                rpc(10, "nature_block_task", {"project_root": tmp, "workflow_dir": workflow_dir, "task_id": "T2", "reason": "rpc blocker"}),
                rpc(11, "nature_log_note", {"project_root": tmp, "workflow_dir": workflow_dir, "note": "rpc note"}),
                rpc(12, "nature_spec", {"project_root": tmp, "workflow_dir": workflow_dir, "status": "skipped"}),
                rpc(13, "nature_memory_remember", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "title": "A", "body": "A body", "metadata": {"kind": "decision"}}),
                rpc(14, "nature_memory_remember", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "title": "B", "body": "B body", "metadata": {"kind": "decision"}}),
                rpc(15, "nature_memory_remember", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "title": "C", "body": "C body", "metadata": {"kind": "decision"}}),
            ]
            second = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, *calls]) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            second_replies = [json.loads(line) for line in second.stdout.splitlines() if line.strip()]
            self.assertEqual(second.returncode, 0, second.stderr)
            for reply in second_replies:
                if reply.get("id") == 1:
                    continue
                self.assertNotIn("error", reply, reply)
                payload = json.loads(reply["result"]["content"][0]["text"])
                self.assertTrue(payload.get("ok"), (reply.get("id"), payload))
            a = json.loads(next(reply for reply in second_replies if reply.get("id") == 13)["result"]["content"][0]["text"])
            b = json.loads(next(reply for reply in second_replies if reply.get("id") == 14)["result"]["content"][0]["text"])
            c = json.loads(next(reply for reply in second_replies if reply.get("id") == 15)["result"]["content"][0]["text"])
            successor_request = rpc(16, "nature_memory_supersede", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "old_id": a["entry_id"], "expected_etag": a["etag"], "new_title": "A successor", "new_body": "A successor body", "new_metadata": {"kind": "decision"}})
            followups = [
                successor_request,
                rpc(17, "nature_memory_recall", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "query": "B"}),
                rpc(18, "nature_memory_show", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "entry_id": a["entry_id"]}),
                rpc(19, "nature_memory_consolidate_plan", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "source_ids": [b["entry_id"], c["entry_id"]]}),
            ]
            third = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, *followups]) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            third_replies = [json.loads(line) for line in third.stdout.splitlines() if line.strip()]
            self.assertEqual(third.returncode, 0, third.stderr)
            for reply in third_replies:
                if reply.get("id") == 1:
                    continue
                self.assertNotIn("error", reply, reply)
            successor = json.loads(next(reply for reply in third_replies if reply.get("id") == 16)["result"]["content"][0]["text"])
            plan = json.loads(next(reply for reply in third_replies if reply.get("id") == 19)["result"]["content"][0]["text"])
            final_calls = [
                rpc(20, "nature_memory_consolidate_apply", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "plan_id": plan["plan_id"], "source_ids": plan["source_ids"], "source_etags": plan["source_etags"], "new_title": "BC", "new_body": "combined", "new_metadata": {"kind": "decision"}}),
                rpc(21, "nature_memory_forget", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "entry_id": successor["entry_id"], "expected_etag": successor["etag"], "reason": "rpc archive"}),
                rpc(22, "nature_memory_migrate", {"project_root": tmp, "scope": "shared", "all_workflows": True, "dry_run": True}),
                rpc(23, "nature_memory_touch", {"project_root": tmp, "workflow_dir": workflow_dir, "entry_id": b["entry_id"]}),
                rpc(24, "nature_memory_index", {"project_root": tmp, "workflow_root": "docs/nature-workflows"}),
                rpc(25, "nature_memory_list", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared"}),
                rpc(26, "nature_resume_with_memory", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared", "query": "B"}),
                rpc(27, "nature_memory_check", {"project_root": tmp, "workflow_dir": workflow_dir, "scope": "shared"}),
            ]
            final = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, *final_calls]) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            final_replies = [json.loads(line) for line in final.stdout.splitlines() if line.strip()]
            self.assertEqual(final.returncode, 0, final.stderr)
            for reply in final_replies:
                if reply.get("id") == 1:
                    continue
                if reply.get("id") == 23:
                    self.assertIn("error", reply, reply)
                    self.assertEqual(reply["error"]["data"]["code"], "invalid_lifecycle_transition", reply)
                    continue
                self.assertNotIn("error", reply, reply)
                payload = json.loads(reply["result"]["content"][0]["text"])
                self.assertTrue(payload.get("ok"), (reply.get("id"), payload))

            def make_facade_workflow(slug: str) -> str:
                proc = subprocess.run(
                    [sys.executable, str(SERVER)],
                    input="\n".join(json.dumps(item, ensure_ascii=False) for item in [
                        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                        rpc(2, "nature_new_workflow", {"project_root": tmp, "slug": slug, "title": slug, "tasks": ["T1: facade"]}),
                    ]) + "\n",
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                reply = next(json.loads(line) for line in proc.stdout.splitlines() if line.strip() and json.loads(line).get("id") == 2)
                payload = json.loads(reply["result"]["content"][0]["text"])
                return payload["workflow_dir"]

            facade_workflow = make_facade_workflow("facade")
            facade_calls = [
                rpc(30, "nature_start_task", {"project_root": tmp, "workflow_dir": facade_workflow, "task_id": "T1"}),
                rpc(31, "nature_complete_with_memory_review", {"project_root": tmp, "workflow_dir": facade_workflow, "scope": "shared", "task_id": "T1", "evidence": "facade evidence"}),
            ]
            facade = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, *facade_calls]) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            facade_replies = [json.loads(line) for line in facade.stdout.splitlines() if line.strip()]
            complete_payload = json.loads(next(reply for reply in facade_replies if reply.get("id") == 31)["result"]["content"][0]["text"])
            self.assertTrue(complete_payload["progress_committed"], complete_payload)
            self.assertIn(complete_payload["memory_review"]["status"], {"available", "partial", "unavailable"})

            block_workflow = make_facade_workflow("block-facade")
            block = subprocess.run(
                [sys.executable, str(SERVER)],
                input="\n".join(json.dumps(item, ensure_ascii=False) for item in [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                    rpc(32, "nature_block_with_memory_review", {"project_root": tmp, "workflow_dir": block_workflow, "scope": "shared", "task_id": "T1", "reason": "facade blocker"}),
                ]) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            block_replies = [json.loads(line) for line in block.stdout.splitlines() if line.strip()]
            block_payload = json.loads(next(reply for reply in block_replies if reply.get("id") == 32)["result"]["content"][0]["text"])
            self.assertTrue(block_payload["progress_committed"], block_payload)

            missing = subprocess.run(
                [sys.executable, str(SERVER)],
                input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "nature_complete_with_memory_review", "arguments": {"project_root": tmp, "scope": "shared", "task_id": "T1", "evidence": "missing workflow"}}}) + "\n",
                text=True,
                capture_output=True,
                timeout=30,
            )
            missing_reply = json.loads(next(line for line in missing.stdout.splitlines() if line.strip()))
            self.assertIn("error", missing_reply)

    def test_real_rpc_preserves_committed_progress_when_memory_review_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            def create_workflow(slug: str) -> str:
                reply = _run_rpc([
                    _tool_call(1, "nature_new_workflow", {
                        "project_root": tmp,
                        "slug": slug,
                        "title": slug,
                        "tasks": ["T1: facade failure"],
                    })
                ])[1]
                payload = json.loads(reply["result"]["content"][0]["text"])
                return payload["workflow_dir"]

            workflow_dir = create_workflow("post-commit-failure")
            memory_path = Path(workflow_dir) / "memory.md"
            memory_path.mkdir()
            complete = _run_rpc([
                _tool_call(2, "nature_start_task", {
                    "project_root": tmp, "workflow_dir": workflow_dir, "task_id": "T1",
                }),
                _tool_call(3, "nature_complete_with_memory_review", {
                    "project_root": tmp,
                    "workflow_dir": workflow_dir,
                    "scope": "shared",
                    "task_id": "T1",
                    "evidence": "committed before review",
                    "max_bytes": 256,
                }),
            ])[3]
            self.assertNotIn("error", complete, complete)
            payload = json.loads(complete["result"]["content"][0]["text"])
            self.assertTrue(payload["progress_committed"], payload)
            self.assertEqual(payload["memory_review"]["status"], "unavailable", payload)
            self.assertEqual(payload["memory_review"]["error"]["code"], "memory_path_not_regular_file", payload)
            self.assertLessEqual(
                len(json.dumps(payload["memory_review"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                256,
                payload,
            )
            resume_reply = _run_rpc([
                _tool_call(8, "nature_resume_with_memory", {
                    "project_root": tmp,
                    "workflow_dir": workflow_dir,
                    "scope": "shared",
                    "query": "post-commit",
                    "max_bytes": 256,
                }),
            ])[8]
            resume_payload = json.loads(resume_reply["result"]["content"][0]["text"])
            self.assertEqual(resume_payload["memory_context"]["status"], "unavailable", resume_payload)
            self.assertLessEqual(
                len(json.dumps(resume_payload["memory_context"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                256,
                resume_payload,
            )

            lost_response_workflow = create_workflow("response-loss")
            lost_memory_path = Path(lost_response_workflow) / "memory.md"
            lost_memory_path.mkdir()
            _run_rpc([
                _tool_call(4, "nature_start_task", {
                    "project_root": tmp, "workflow_dir": lost_response_workflow, "task_id": "T1",
                }),
                _tool_call(5, "nature_complete_with_memory_review", {
                    "project_root": tmp,
                    "workflow_dir": lost_response_workflow,
                    "scope": "shared",
                    "task_id": "T1",
                    "evidence": "response was lost after commit",
                }),
            ])
            recovery = _run_rpc([
                _tool_call(6, "nature_status", {
                    "project_root": tmp, "workflow_dir": lost_response_workflow,
                }),
                _tool_call(7, "nature_resume", {
                    "project_root": tmp, "workflow_dir": lost_response_workflow,
                }),
            ])
            status_payload = json.loads(recovery[6]["result"]["content"][0]["text"])
            resume_payload = json.loads(recovery[7]["result"]["content"][0]["text"])
            self.assertEqual(status_payload["status"], "completed", status_payload)
            self.assertEqual(status_payload["task_counts"]["completed"], 1, status_payload)
            self.assertEqual(resume_payload["resume_state"], "completed", resume_payload)


if __name__ == "__main__":
    unittest.main()
