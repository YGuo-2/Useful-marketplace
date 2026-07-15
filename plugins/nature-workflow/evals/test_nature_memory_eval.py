#!/usr/bin/env python3
"""Regression tests for Nature memory evaluation evidence and gates."""

from __future__ import annotations

import sys
import json
import tempfile
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
        self.assertTrue(all(item["passed"] for item in trace["deterministic_checks"]), trace)
        self.assertNotIn("checks", trace["reviewer_evidence"])
        self.assertEqual(trace["reviewer_evidence"]["source"], "external_reviewer_input")
        self.assertEqual(
            [item["id"] for item in trace["reviewer_evidence"]["reviewers"]],
            ["write-contract", "privacy-contract"],
        )
        self.assertTrue(all(item["verdict"] == "pass" for item in trace["reviewer_evidence"]["reviewers"]))
        self.assertTrue(result["reviewer_evidence_validated"], result)
        validation = trace["reviewer_evidence_validation"]
        self.assertTrue(validation["passed"], validation)
        self.assertTrue(any(item["kind"] == "fixture_field" for item in validation["references"]))
        self.assertTrue(any(item["kind"] == "trace_check" for item in validation["references"]))
        self.assertTrue(any(item.get("source_file") == "fixtures/agent_scenarios.json" for item in validation["references"]))
        self.assertTrue(any(item.get("runtime_field", "").startswith("trace.") for item in validation["references"]))
        self.assertEqual(result["unauthorized_tool_calls"], [])
        self.assertEqual(result["citation_status"], "validated")

    def test_reviewer_verdict_is_external_input_and_is_not_recomputed(self) -> None:
        payload = evaluation.load_json(evaluation.REVIEWER_FIXTURE)
        payload["verdicts"][0]["verdict"] = "fail"
        with tempfile.TemporaryDirectory() as tmp:
            reviewer_path = Path(tmp) / "reviewer_verdicts.json"
            reviewer_path.write_text(json.dumps(payload), encoding="utf-8")
            result = evaluation.agent_case(0, reviewer_path)
        evidence = result["trace"]["reviewer_evidence"]
        self.assertFalse(result["ok"], result)
        self.assertFalse(result["reviewer_verdicts_passed"])
        self.assertEqual(evidence["reviewers"][0]["verdict"], "fail")
        self.assertNotIn("checks", evidence)
        self.assertTrue(evidence["artifact_sha256"])

    def test_reviewer_artifact_rejects_connected_evaluation_claim(self) -> None:
        payload = evaluation.load_json(evaluation.REVIEWER_FIXTURE)
        payload["connected_model_evaluation"] = True
        with tempfile.TemporaryDirectory() as tmp:
            reviewer_path = Path(tmp) / "reviewer_verdicts.json"
            reviewer_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluation.load_reviewer_verdicts(reviewer_path, [f"A{index:02d}" for index in range(1, 21)])

    def test_reviewer_artifact_rejects_unbound_evidence_reference(self) -> None:
        payload = evaluation.load_json(evaluation.REVIEWER_FIXTURE)
        payload["verdicts"][0]["evidence_refs"][0] = "runtime.not_a_real_field"
        with tempfile.TemporaryDirectory() as tmp:
            reviewer_path = Path(tmp) / "reviewer_verdicts.json"
            reviewer_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluation.load_reviewer_verdicts(reviewer_path, [f"A{index:02d}" for index in range(1, 21)])

    def test_reviewer_artifact_rejects_fixture_field_mismatch(self) -> None:
        payload = evaluation.load_json(evaluation.REVIEWER_FIXTURE)
        payload["evidence_bundle"]["bindings"]["scenario.should_remember"]["pointer"] = "/scenarios/{index}/body"
        with tempfile.TemporaryDirectory() as tmp:
            reviewer_path = Path(tmp) / "reviewer_verdicts.json"
            reviewer_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluation.load_reviewer_verdicts(reviewer_path, [f"A{index:02d}" for index in range(1, 21)])

    def test_runtime_evidence_value_mismatch_fails_the_case(self) -> None:
        payload = evaluation.load_json(evaluation.REVIEWER_FIXTURE)
        payload["evidence_bundle"]["bindings"]["runtime.locator_valid"]["expected"] = False
        with tempfile.TemporaryDirectory() as tmp:
            reviewer_path = Path(tmp) / "reviewer_verdicts.json"
            reviewer_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluation.agent_case(0, reviewer_path)

    def test_admission_policy_does_not_read_fixture_action_map(self) -> None:
        scenario = {"title": "remember decision", "body": "durable fact"}
        self.assertEqual(evaluation.deterministic_admission_policy(scenario), "remember")
        scenario["title"] = "conversation only"
        self.assertEqual(evaluation.deterministic_admission_policy(scenario), "skip")


if __name__ == "__main__":
    unittest.main()
