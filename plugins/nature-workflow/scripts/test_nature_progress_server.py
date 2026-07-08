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


if __name__ == "__main__":
    unittest.main()
