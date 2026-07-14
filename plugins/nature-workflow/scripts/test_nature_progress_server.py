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


if __name__ == "__main__":
    unittest.main()
