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


if __name__ == "__main__":
    unittest.main()
