#!/usr/bin/env python3
"""Regression tests for Nature memory evaluation evidence and gates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import nature_memory_eval as evaluation  # noqa: E402


class NatureMemoryEvalTests(unittest.TestCase):
    def test_deterministic_eval_gates_each_slice_and_canonical_workload(self) -> None:
        result = evaluation.deterministic_eval()
        self.assertTrue(result["ok"], result)
        self.assertEqual(set(result["slice_gates"]), {"exact", "partial", "mixed", "no_hit"})
        self.assertTrue(all(gate["passed"] for gate in result["slice_gates"].values()))
        self.assertTrue(all(result["coverage_checks"].values()), result["coverage_checks"])
        self.assertTrue(all(result["benchmark_checks"].values()), result["benchmark_checks"])
        self.assertEqual(result["benchmark"]["single_workflow_bytes"], 256 * 1024)
        self.assertTrue(any(event["event"] == "gates_evaluated" for event in result["trace"]))
        self.assertTrue(result["platform_evidence"]["real_runtime_only"])

    def test_agent_case_records_policy_trace_snapshot_and_reviewer_checks(self) -> None:
        result = evaluation.agent_case(0)
        self.assertTrue(result["ok"], result)
        trace = result["trace"]
        self.assertEqual(trace["policy"], "local-deterministic-prompt-policy")
        self.assertTrue(trace["tool_calls"])
        self.assertIn("project_snapshot_before", trace)
        self.assertIn("project_snapshot_after", trace)
        self.assertTrue(all(item["passed"] for item in trace["reviewer_evidence"]["checks"]), trace)
        self.assertEqual(result["unauthorized_tool_calls"], [])
        self.assertEqual(result["citation_status"], "validated")

    def test_admission_policy_does_not_read_fixture_action_map(self) -> None:
        scenario = {"title": "remember decision", "body": "durable fact"}
        self.assertEqual(evaluation.deterministic_admission_policy(scenario), "remember")
        scenario["title"] = "conversation only"
        self.assertEqual(evaluation.deterministic_admission_policy(scenario), "skip")


if __name__ == "__main__":
    unittest.main()
