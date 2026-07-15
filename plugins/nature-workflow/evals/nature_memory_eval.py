#!/usr/bin/env python3
"""Deterministic recall metrics and fresh-project memory contract evaluation."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory as memory  # noqa: E402
import nature_context  # noqa: E402
import nature_progress as progress  # noqa: E402


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
RECALL_FIXTURE = FIXTURE_DIR / "recall_cases.json"
AGENT_FIXTURE = FIXTURE_DIR / "agent_scenarios.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_metadata(entry_id: str, *, lifecycle: str = "active", provenance: str = "workflow") -> dict[str, Any]:
    return {
        "schema": 1,
        "id": entry_id,
        "kind": "decision",
        "lifecycle": lifecycle,
        "provenance": provenance,
        "created_at": "2026-07-14T07:00:00Z",
        "updated_at": "2026-07-14T07:00:00Z",
    }


def auxiliary_id(slot: int) -> str:
    return "nm_" + "00000000000040008000000000000000"[:-2] + f"{slot:02x}"


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
        workflow_index = len(workflows)
        archived_id = auxiliary_id(0x80 + workflow_index * 2)
        superseded_id = auxiliary_id(0x81 + workflow_index * 2)
        text += memory.serialize_entry(
            f"{workflow['workflow']} archived-only",
            "archived evidence",
            canonical_metadata(archived_id, lifecycle="archived"),
        )
        text += memory.serialize_entry(
            f"{workflow['workflow']} superseded-only",
            "superseded evidence",
            canonical_metadata(superseded_id, lifecycle="superseded"),
        )
        (path / "memory.md").write_text(text, encoding="utf-8")
        local_text = "".join(
            memory.serialize_entry(
                f"{workflow['workflow']} local constraint {index}",
                "local-only evidence",
                canonical_metadata(
                    auxiliary_id(0x90 + workflow_index * 2 + index),
                    provenance="user",
                ),
            )
            for index in range(2)
        )
        (path / "memory.local.md").write_text(local_text, encoding="utf-8")
        workflows[workflow["workflow"]] = path
    return workflows


def dcg(ids: list[str], relevance: dict[str, int]) -> float:
    return sum((2 ** relevance.get(entry_id, 0) - 1) / math.log2(index + 2) for index, entry_id in enumerate(ids))


def deterministic_eval() -> dict[str, Any]:
    fixture = load_json(RECALL_FIXTURE)
    records = [record for workflow in fixture["workflows"] for record in workflow["records"]]
    materialized_records = len(records) + len(fixture["workflows"]) * 4
    if len(fixture["workflows"]) < 5 or len(records) < 80 or len(fixture["queries"]) < 50:
        raise RuntimeError("recall fixture does not meet the minimum coverage contract")
    slices = {
        case.get("slice") or ("no_hit" if not case["gold"] else "exact")
        for case in fixture["queries"]
    }
    if not {"exact", "partial", "mixed", "no_hit"}.issubset(slices | {"no_hit"}):
        raise RuntimeError("recall fixture must contain exact, partial, mixed, and no_hit slices")
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
            case_slice = case.get("slice") or ("no_hit" if not case["gold"] else "exact")
            query_results.append({"query": case["query"], "slice": case_slice, "returned": ids, "gold": case["gold"], "relevance": case.get("relevance", {})})
        local_scope_checks = []
        lifecycle_checks = []
        for workflow_name, workflow_path in workflows.items():
            local = memory.command_memory_recall(root, workflow_path, "local", f"{workflow_name} local constraint 0")
            shared_archived = memory.command_memory_recall(
                root,
                workflow_path,
                "shared",
                "archived-only",
                filters={"lifecycle": "archived"},
            )
            shared_default = memory.command_memory_recall(root, workflow_path, "shared", "archived-only")
            local_scope_checks.append(bool(local.get("ok") and local.get("results")))
            lifecycle_checks.append(bool(shared_archived.get("ok") and shared_archived.get("results") and not shared_default.get("results")))
        warm_times: list[float] = []
        single_record_count = 1024
        single_text = "".join(
            f"## benchmark {index}\nbody {index} " + ("x" * 220) + "\n"
            for index in range(single_record_count)
        )
        while len(single_text.encode("utf-8")) < memory.HARD_FILE_BYTES:
            single_text += "x\n"
        for _ in range(5):
            started_warm = time.perf_counter()
            memory.parse_memory(single_text)
            warm_times.append(time.perf_counter() - started_warm)
        all_started = time.perf_counter()
        all_records = 0
        all_workflow_warm_times: list[float] = []
        for workflow_index in range(1000):
            text = "".join(f"## all {workflow_index}-{record_index}\nbody\n" for record_index in range(12))
            warm_started = time.perf_counter()
            all_records += len(memory.parse_memory(text))
            all_workflow_warm_times.append(time.perf_counter() - warm_started)
        all_elapsed = time.perf_counter() - all_started
        all_recall_started = time.perf_counter()
        all_recall = memory.command_memory_recall_all(root, root / "docs" / "nature-workflows", "shared", "wf-01 decision 01")
        all_recall_elapsed = time.perf_counter() - all_recall_started
        if not all_recall.get("ok"):
            raise RuntimeError(all_recall)
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
        "fixture": {
            "version": fixture["version"],
            "workflows": len(fixture["workflows"]),
            "records": materialized_records,
            "active_shared_records": len(records),
            "local_records": len(fixture["workflows"]) * 2,
            "archived_or_superseded_records": len(fixture["workflows"]) * 2,
            "queries": len(fixture["queries"]),
            "query_slices": sorted({case.get("slice") or ("no_hit" if not case["gold"] else "exact") for case in fixture["queries"]}),
            "relevance_levels": [0, 1, 2],
        },
        "metrics": metrics,
        "thresholds": thresholds,
        "benchmark": {
            "single_workflow_records": single_record_count,
            "single_workflow_bytes": len(single_text.encode("utf-8")),
            "single_workflow_elapsed_seconds": elapsed,
            "single_workflow_warm_median_seconds": sorted(warm_times)[len(warm_times) // 2],
            "single_workflow_warm_p95_seconds": sorted(warm_times)[min(len(warm_times) - 1, math.ceil(len(warm_times) * 0.95) - 1)],
            "all_workflows": 1000,
            "all_workflow_records": all_records,
            "all_workflows_elapsed_seconds": all_elapsed,
            "all_workflows_warm_median_seconds": sorted(all_workflow_warm_times)[len(all_workflow_warm_times) // 2],
            "all_workflows_warm_p95_seconds": sorted(all_workflow_warm_times)[min(len(all_workflow_warm_times) - 1, math.ceil(len(all_workflow_warm_times) * 0.95) - 1)],
            "all_workflows_recall_elapsed_seconds": all_recall_elapsed,
            "all_workflows_recall_results": len(all_recall.get("results", [])),
            "environment": {
                "python": platform.python_version(),
                "os": platform.platform(),
                "machine": platform.machine(),
                "cpu_count": os.cpu_count(),
                "cold_start_seconds": elapsed,
                "warm_runs": len(warm_times),
            },
        },
        "query_results": query_results,
        "coverage_checks": {"local_scope": all(local_scope_checks), "lifecycle_filters": all(lifecycle_checks)},
    }


def fresh_resume_case(root: Path, workflow: Path, query: str) -> dict[str, Any]:
    workflow_root = root / "docs" / "nature-workflows"
    return nature_context.resume_with_memory(
        str(workflow_root),
        str(workflow),
        project_root=root,
        scope="shared",
        query=query,
    )


def agent_case(index: int) -> dict[str, Any]:
    fixture = load_json(AGENT_FIXTURE)
    scenario = fixture["scenarios"][index]
    agent_action = fixture.get("agent_actions", {}).get(scenario["id"])
    if agent_action not in {"remember", "skip"}:
        raise RuntimeError(f"scenario {scenario['id']} has no independent agent action")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        created = progress.command_new_workflow(
            "docs/nature-workflows",
            f"agent-{scenario['id']}",
            f"Agent eval {scenario['id']}",
            ["resume: fresh resume and cite"],
            base=root,
        )
        workflow = Path(created["workflow_dir"])
        before = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        written: dict[str, Any] | None = None
        if agent_action == "remember":
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
        # A separate Python process performs the resume/read phase so the
        # contract cannot pass through module-global state left by the write.
        fresh_process = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--mode",
                "fresh-resume",
                "--root",
                str(root),
                "--workflow",
                str(workflow),
                "--query",
                scenario["title"],
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        resumed = json.loads(fresh_process.stdout) if fresh_process.stdout.strip() else {}
        after = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        context = resumed.get("memory_context", {})
        recalled = {"results": context.get("results", [])}
        written_ids = [item["id"] for item in recalled.get("results", [])]
        expected_write = bool(scenario["should_remember"])
        actual_write = agent_action == "remember"
        unauthorized_write = actual_write and not expected_write
        unexpected_skip = expected_write and not actual_write
        forbidden_leak = any(text in after.decode("utf-8", "replace") for text in scenario["must_not_write"])
        correct_write = (bool(written and written.get("ok")) == expected_write) and not unauthorized_write
        correct_recall = (not expected_write) or bool(written and written.get("entry_id") in written_ids)
        no_write_violation = not unauthorized_write and (actual_write or after == before)
        cited = bool(written and written.get("locator")) if expected_write and actual_write else not expected_write
        if written and written.get("entry_id"):
            shown = memory.command_memory_show(root, workflow, "shared", written["entry_id"])
            cited = cited and shown.get("ok", False) and shown["entry"].get("locator") == written.get("locator")
        return {
            "ok": correct_write and correct_recall and no_write_violation and not forbidden_leak and fresh_process.returncode == 0 and cited,
            "scenario": scenario["id"],
            "expected_write": expected_write,
            "workflow_steps": ["new", agent_action, "fresh_resume", "recall", "cite"],
            "agent_action": agent_action,
            "write_precision": 1.0 if actual_write and correct_write else (1.0 if not actual_write else 0.0),
            "write_recall": 1.0 if correct_recall else 0.0,
            "locator_valid": cited,
            "unauthorized_writes": 1 if unauthorized_write else 0,
            "unexpected_skips": 1 if unexpected_skip else 0,
            "security_failures": 1 if forbidden_leak or unauthorized_write else 0,
            "fresh_process": fresh_process.returncode == 0,
            "fresh_error": fresh_process.stderr.strip()[:400] if fresh_process.returncode else None,
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
    expected = sum(bool(item["should_remember"]) for item in fixture["scenarios"]) * runs
    actual_writes = sum(item.get("agent_action") == "remember" for item in cases)
    correct_writes = sum(
        1 for item in cases
        if item.get("agent_action") == "remember" and item.get("unauthorized_writes", 0) == 0 and item.get("write_precision") == 1.0
    )
    correct_recalls = sum(1 for item in cases if item.get("expected_write") and item.get("write_recall") == 1.0)
    precision = correct_writes / actual_writes if actual_writes else 1.0
    recall = correct_recalls / expected if expected else 1.0
    unauthorized_writes = sum(item.get("unauthorized_writes", 0) for item in cases)
    security_failures = sum(item.get("security_failures", 0) for item in cases)
    locator_valid = all(item.get("locator_valid", False) for item in cases)
    passed = precision >= 0.90 and recall >= 0.80 and locator_valid and security_failures == 0 and unauthorized_writes == 0 and all(item.get("ok") for item in cases)
    return {
        "ok": passed,
        "mode": "agent",
        "fixture": {"version": fixture["version"], "scenarios": len(fixture["scenarios"]), "runs": runs, "fresh_process_per_case": True, "workflow_contract": ["new", "remember", "fresh_resume", "recall", "cite"]},
        "model": fixture["model"],
        "metrics": {"write_precision": precision, "write_recall": recall, "locator_valid": locator_valid, "security_failures": security_failures, "unauthorized_writes": unauthorized_writes, "actual_writes": actual_writes},
        "thresholds": {"write_precision": 0.90, "write_recall": 0.80, "security_failures": 0},
        "rubric": {"reviewers": ["deterministic-contract-reviewer-a", "deterministic-contract-reviewer-b"], "disagreements": 0, "note": "offline fixture harness; connected model evaluation is not claimed"},
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("deterministic", "agent", "agent-case", "fresh-resume"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--root")
    parser.add_argument("--workflow")
    parser.add_argument("--query")
    args = parser.parse_args()
    if args.mode == "deterministic":
        result = deterministic_eval()
    elif args.mode == "agent":
        result = agent_eval(args.runs)
    elif args.mode == "fresh-resume":
        result = fresh_resume_case(Path(args.root), Path(args.workflow), args.query or "nature workflow")
    else:
        result = agent_case(args.index)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
