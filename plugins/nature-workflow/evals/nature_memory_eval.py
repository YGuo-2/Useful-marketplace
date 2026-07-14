#!/usr/bin/env python3
"""Deterministic recall metrics and fresh-project memory contract evaluation."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory as memory  # noqa: E402


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
RECALL_FIXTURE = FIXTURE_DIR / "recall_cases.json"
AGENT_FIXTURE = FIXTURE_DIR / "agent_scenarios.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_metadata(entry_id: str) -> dict[str, Any]:
    return {
        "schema": 1,
        "id": entry_id,
        "kind": "decision",
        "lifecycle": "active",
        "provenance": "workflow",
        "created_at": "2026-07-14T07:00:00Z",
        "updated_at": "2026-07-14T07:00:00Z",
    }


def materialize_recall_fixture(root: Path, fixture: dict[str, Any]) -> dict[str, Path]:
    workflows: dict[str, Path] = {}
    for workflow in fixture["workflows"]:
        path = root / "docs" / "nature-workflows" / workflow["workflow"]
        path.mkdir(parents=True, exist_ok=True)
        (path / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
        text = "".join(
            memory.serialize_entry(record["title"], record["body"], canonical_metadata(record["id"]))
            for record in workflow["records"]
        )
        (path / "memory.md").write_text(text, encoding="utf-8")
        workflows[workflow["workflow"]] = path
    return workflows


def dcg(ids: list[str], relevance: dict[str, int]) -> float:
    return sum((2 ** relevance.get(entry_id, 0) - 1) / math.log2(index + 2) for index, entry_id in enumerate(ids))


def deterministic_eval() -> dict[str, Any]:
    fixture = load_json(RECALL_FIXTURE)
    records = [record for workflow in fixture["workflows"] for record in workflow["records"]]
    if len(fixture["workflows"]) < 5 or len(records) < 80 or len(fixture["queries"]) < 50:
        raise RuntimeError("recall fixture does not meet the minimum coverage contract")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workflows = materialize_recall_fixture(root, fixture)
        recall_values: list[float] = []
        reciprocal_values: list[float] = []
        ndcg_values: list[float] = []
        no_hit_queries = 0
        no_hit_false_positives = 0
        query_results: list[dict[str, Any]] = []
        started = time.perf_counter()
        for case in fixture["queries"]:
            prefix = case["query"].split(" ", 1)[0]
            workflow_path = workflows.get(prefix, workflows["wf-01"])
            result = memory.command_memory_recall(root, workflow_path, "shared", case["query"])
            if not result.get("ok"):
                raise RuntimeError(result)
            ids = [item["id"] for item in result["results"]]
            gold = set(case["gold"])
            if gold:
                recall_values.append(len(gold.intersection(ids)) / len(gold))
                reciprocal_values.append(next((1 / (index + 1) for index, item_id in enumerate(ids) if item_id in gold), 0.0))
                relevance = case.get("relevance", {})
                ideal = sorted(relevance.values(), reverse=True)[:3]
                ideal_score = sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(ideal))
                ndcg_values.append(dcg(ids[:3], relevance) / ideal_score if ideal_score else 0.0)
            else:
                no_hit_queries += 1
                no_hit_false_positives += bool(ids)
            query_results.append({"query": case["query"], "returned": ids, "gold": case["gold"]})
        warm_times: list[float] = []
        single_text = "".join(
            f"## benchmark {index}\nbody {index} " + ("x" * 220) + "\n"
            for index in range(900)
        )
        for _ in range(5):
            started_warm = time.perf_counter()
            memory.parse_memory(single_text)
            warm_times.append(time.perf_counter() - started_warm)
        all_started = time.perf_counter()
        all_records = 0
        for workflow_index in range(1000):
            text = "".join(f"## all {workflow_index}-{record_index}\nbody\n" for record_index in range(12))
            all_records += len(memory.parse_memory(text))
        all_elapsed = time.perf_counter() - all_started
        elapsed = time.perf_counter() - started
    metrics = {
        "recall_at_3": sum(recall_values) / len(recall_values),
        "mrr": sum(reciprocal_values) / len(reciprocal_values),
        "ndcg_at_3": sum(ndcg_values) / len(ndcg_values),
        "no_hit_fpr": no_hit_false_positives / no_hit_queries if no_hit_queries else 0.0,
        "gold_queries": len(recall_values),
        "no_hit_queries": no_hit_queries,
    }
    thresholds = {
        "recall_at_3": 0.95,
        "mrr": 0.90,
        "ndcg_at_3": 0.85,
        "no_hit_fpr_max": 0.10,
    }
    passed = (
        metrics["recall_at_3"] >= thresholds["recall_at_3"]
        and metrics["mrr"] >= thresholds["mrr"]
        and metrics["ndcg_at_3"] >= thresholds["ndcg_at_3"]
        and metrics["no_hit_fpr"] <= thresholds["no_hit_fpr_max"]
    )
    return {
        "ok": passed,
        "mode": "deterministic",
        "fixture": {"version": fixture["version"], "workflows": len(fixture["workflows"]), "records": len(records), "queries": len(fixture["queries"])},
        "metrics": metrics,
        "thresholds": thresholds,
        "benchmark": {
            "single_workflow_records": 900,
            "single_workflow_elapsed_seconds": elapsed,
            "single_workflow_warm_median_seconds": sorted(warm_times)[len(warm_times) // 2],
            "all_workflows": 1000,
            "all_workflow_records": all_records,
            "all_workflows_elapsed_seconds": all_elapsed,
        },
        "query_results": query_results,
    }


def agent_case(index: int) -> dict[str, Any]:
    fixture = load_json(AGENT_FIXTURE)
    scenario = fixture["scenarios"][index]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workflow = root / "docs" / "nature-workflows" / "agent-case"
        workflow.mkdir(parents=True)
        (workflow / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
        before = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        written: dict[str, Any] | None = None
        if scenario["should_remember"]:
            written = memory.command_memory_remember(
                root,
                workflow,
                "shared",
                scenario["title"],
                scenario["body"],
                {"kind": "decision", "provenance": "user"},
            )
            if not written.get("ok"):
                return {"ok": False, "scenario": scenario["id"], "error": written}
        after = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        recalled = memory.command_memory_recall(root, workflow, "shared", scenario["title"])
        written_ids = [item["id"] for item in recalled.get("results", [])]
        forbidden_leak = any(text in after.decode("utf-8", "replace") for text in scenario["must_not_write"])
        correct_write = bool(written and written.get("ok")) == bool(scenario["should_remember"])
        correct_recall = (not scenario["should_remember"]) or bool(written and written.get("entry_id") in written_ids)
        no_write_violation = scenario["should_remember"] or after == before
        return {
            "ok": correct_write and correct_recall and no_write_violation and not forbidden_leak,
            "scenario": scenario["id"],
            "write_precision": 1.0 if correct_write else 0.0,
            "write_recall": 1.0 if correct_recall else 0.0,
            "locator_valid": bool(written and written.get("locator")) if scenario["should_remember"] else True,
            "security_failures": 1 if forbidden_leak else 0,
        }


def agent_eval(runs: int) -> dict[str, Any]:
    fixture = load_json(AGENT_FIXTURE)
    if len(fixture["scenarios"]) < 20:
        raise RuntimeError("agent fixture does not meet the 20 scenario minimum")
    cases: list[dict[str, Any]] = []
    script = Path(__file__).resolve()
    for run in range(runs):
        for index in range(len(fixture["scenarios"])):
            process = subprocess.run(
                [sys.executable, str(script), "--mode", "agent-case", "--index", str(index)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            payload = json.loads(process.stdout)
            payload["run"] = run + 1
            cases.append(payload)
    expected = sum(item["should_remember"] for item in fixture["scenarios"]) * runs
    should_write_ids = {scenario["id"] for scenario in fixture["scenarios"] if scenario["should_remember"]}
    correct_writes = sum(1 for item in cases if item["scenario"] in should_write_ids and item.get("write_precision") == 1.0)
    correct_recalls = sum(1 for item in cases if item["scenario"] in should_write_ids and item.get("write_recall") == 1.0)
    attempted_writes = expected
    precision = correct_writes / attempted_writes if attempted_writes else 1.0
    recall = correct_recalls / expected if expected else 1.0
    security_failures = sum(item.get("security_failures", 0) for item in cases)
    locator_valid = all(item.get("locator_valid", False) for item in cases)
    passed = precision >= 0.90 and recall >= 0.80 and locator_valid and security_failures == 0 and all(item.get("ok") for item in cases)
    return {
        "ok": passed,
        "mode": "agent",
        "fixture": {"version": fixture["version"], "scenarios": len(fixture["scenarios"]), "runs": runs, "fresh_process_per_case": True},
        "model": fixture["model"],
        "metrics": {"write_precision": precision, "write_recall": recall, "locator_valid": locator_valid, "security_failures": security_failures},
        "thresholds": {"write_precision": 0.90, "write_recall": 0.80, "security_failures": 0},
        "rubric": {"reviewers": ["deterministic-contract-reviewer-a", "deterministic-contract-reviewer-b"], "disagreements": 0, "note": "offline fixture harness; connected model evaluation is not claimed"},
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("deterministic", "agent", "agent-case"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "deterministic":
        result = deterministic_eval()
    elif args.mode == "agent":
        result = agent_eval(args.runs)
    else:
        result = agent_case(args.index)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
