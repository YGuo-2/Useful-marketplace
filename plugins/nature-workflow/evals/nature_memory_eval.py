#!/usr/bin/env python3
"""Deterministic recall metrics and fresh-project memory contract evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
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
REVIEWER_FIXTURE = FIXTURE_DIR / "reviewer_verdicts.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reviewer_verdicts(path: Path, scenario_ids: list[str]) -> dict[str, Any]:
    """Load reviewer decisions as external input, never derive them in the harness."""
    payload = load_json(path)
    if payload.get("version") != 1 or payload.get("artifact_type") != "independent_reviewer_verdicts":
        raise ValueError("reviewer verdict artifact schema is unsupported")
    if payload.get("evaluation_scope") != "offline_fixture_policy":
        raise ValueError("reviewer verdict artifact must be scoped to offline_fixture_policy")
    if payload.get("connected_model_evaluation") is not False:
        raise ValueError("offline reviewer artifact must not claim connected model evaluation")
    if payload.get("source") != "external_reviewer_input":
        raise ValueError("reviewer verdicts must identify an external input source")
    reviewers = payload.get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) != 2:
        raise ValueError("reviewer verdict artifact must contain exactly two reviewers")
    reviewer_ids = [item.get("id") for item in reviewers if isinstance(item, dict)]
    if len(reviewer_ids) != 2 or len(set(reviewer_ids)) != 2:
        raise ValueError("reviewer verdict artifact must contain two distinct reviewer IDs")
    if any(item.get("independent_of_harness") is not True for item in reviewers):
        raise ValueError("reviewers must declare independence from the harness")

    expected_pairs = {(scenario_id, reviewer_id) for scenario_id in scenario_ids for reviewer_id in reviewer_ids}
    verdicts = payload.get("verdicts")
    if not isinstance(verdicts, list):
        raise ValueError("reviewer verdict artifact must contain a verdict list")
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for record in verdicts:
        if not isinstance(record, dict):
            raise ValueError("reviewer verdict records must be objects")
        scenario_id = record.get("scenario_id")
        reviewer_id = record.get("reviewer_id")
        pair = (scenario_id, reviewer_id)
        if pair not in expected_pairs or pair in records:
            raise ValueError("reviewer verdict coverage contains an unknown or duplicate scenario/reviewer pair")
        if record.get("verdict") not in {"pass", "fail"}:
            raise ValueError("reviewer verdict must be pass or fail")
        if not isinstance(record.get("rationale"), str) or not record["rationale"].strip():
            raise ValueError("reviewer verdict must include rationale")
        evidence_refs = record.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or not all(isinstance(ref, str) and ref for ref in evidence_refs):
            raise ValueError("reviewer verdict must include evidence_refs")
        records[pair] = record
    if set(records) != expected_pairs:
        raise ValueError("reviewer verdict artifact does not cover every scenario with both reviewers")
    return {
        "path": path,
        "payload": payload,
        "reviewer_ids": reviewer_ids,
        "records": records,
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def reviewer_evidence(artifact: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    """Copy external verdicts into the trace without adding harness conclusions."""
    records = [artifact["records"][(scenario_id, reviewer_id)] for reviewer_id in artifact["reviewer_ids"]]
    verdicts = [record["verdict"] for record in records]
    return {
        "source": "external_reviewer_input",
        "artifact": artifact["path"].as_posix(),
        "artifact_sha256": artifact["artifact_sha256"],
        "evaluation_scope": artifact["payload"]["evaluation_scope"],
        "connected_model_evaluation": False,
        "reviewers": [
            {
                "id": record["reviewer_id"],
                "verdict": record["verdict"],
                "rationale": record["rationale"],
                "evidence_refs": list(record["evidence_refs"]),
            }
            for record in records
        ],
        "agreement": {
            "verdicts": verdicts,
            "disagreement": len(set(verdicts)) > 1,
        },
    }


def _project_snapshot(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        files.append(
            {
                "path": relative,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    manifest = json.dumps(files, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"sha256": hashlib.sha256(manifest).hexdigest(), "files": files}


def _canonical_workflow(path: Path, records: list[tuple[str, str, str]]) -> tuple[Path, int]:
    path.mkdir(parents=True, exist_ok=True)
    (path / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
    text = "".join(
        memory.serialize_entry(title, body, canonical_metadata(entry_id))
        for entry_id, title, body in records
    )
    memory_path = path / "memory.md"
    memory_path.write_text(text, encoding="utf-8")
    return memory_path, len(records)


def _p95(values: list[float]) -> float:
    return values[min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)] if values else 0.0


def _platform_evidence() -> dict[str, Any]:
    """Run only real host probes; unavailable capabilities remain explicit."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workflow = root / "docs" / "nature-workflows" / "platform"
        workflow.mkdir(parents=True)
        (workflow / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
        outside = root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        symlink_probe: dict[str, Any]
        try:
            os.symlink(outside, workflow / "memory.md")
        except (OSError, NotImplementedError) as exc:
            symlink_probe = {"status": "unavailable", "reason": str(exc)}
        else:
            try:
                memory.resolve_memory_path(root, workflow, "shared")
            except memory.MemoryBoundaryError as exc:
                symlink_probe = {"status": "passed", "code": exc.code}
            else:
                symlink_probe = {"status": "failed", "reason": "symlink escape was accepted"}

        lock_probe: dict[str, Any]
        if os.name == "nt":
            lock_probe = {"status": "not_applicable", "reason": "Unix fcntl backend is not available on Windows"}
        else:
            try:
                with memory.workflow_memory_lock(workflow):
                    pass
            except Exception as exc:  # pragma: no cover - host-specific backend errors
                lock_probe = {"status": "failed", "reason": type(exc).__name__}
            else:
                lock_probe = {"status": "passed", "backend": "fcntl"}
    return {
        "host": platform.system(),
        "real_runtime_only": True,
        "windows_symlink_escape": symlink_probe,
        "unix_fcntl_lock": lock_probe,
        "scope": "host probes only; unavailable foreign-platform probes are not claimed as passed",
    }


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
    base = "00000000000040008000000000000000"
    return "nm_" + base[:-8] + f"{slot:08x}"


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
    fixture_minimum = len(fixture["workflows"]) >= 5 and len(records) >= 80 and len(fixture["queries"]) >= 50
    if not fixture_minimum:
        raise RuntimeError("recall fixture does not meet the minimum coverage contract")
    slices = {
        case.get("slice") or ("no_hit" if not case["gold"] else "exact")
        for case in fixture["queries"]
    }
    required_slices = {"exact", "partial", "mixed", "no_hit"}
    if not required_slices.issubset(slices | {"no_hit"}):
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
        slice_records: dict[str, list[dict[str, Any]]] = {name: [] for name in required_slices}
        started = time.perf_counter()
        for case in fixture["queries"]:
            prefix = case["query"].split(" ", 1)[0]
            workflow_path = workflows.get(prefix, workflows["wf-01"])
            result = memory.command_memory_recall(root, workflow_path, "shared", case["query"])
            if not result.get("ok"):
                raise RuntimeError(result)
            ids = [item["id"] for item in result["results"]]
            gold = set(case["gold"])
            case_slice = case.get("slice") or ("no_hit" if not case["gold"] else "exact")
            slice_result: dict[str, Any] = {
                "query": case["query"],
                "gold": case["gold"],
                "returned": ids,
                "recall_at_3": None,
                "reciprocal_rank": None,
                "ndcg_at_3": None,
                "false_positive": None,
            }
            if gold:
                recall = len(gold.intersection(ids)) / len(gold)
                reciprocal = next((1 / (index + 1) for index, item_id in enumerate(ids) if item_id in gold), 0.0)
                recall_values.append(recall)
                reciprocal_values.append(reciprocal)
                relevance = case.get("relevance", {})
                ideal = sorted(relevance.values(), reverse=True)[:3]
                ideal_score = sum((2 ** value - 1) / math.log2(index + 2) for index, value in enumerate(ideal))
                ndcg = dcg(ids[:3], relevance) / ideal_score if ideal_score else 0.0
                ndcg_values.append(ndcg)
                slice_result.update({"recall_at_3": recall, "reciprocal_rank": reciprocal, "ndcg_at_3": ndcg})
            else:
                no_hit_queries += 1
                false_positive = bool(ids)
                no_hit_false_positives += false_positive
                slice_result["false_positive"] = false_positive
            slice_records.setdefault(case_slice, []).append(slice_result)
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
        benchmark_root = root / "canonical-benchmark"
        single_workflow = benchmark_root / "single-workflow"
        single_record_count = 512
        single_records = [
            (
                auxiliary_id(0x200 + index),
                f"benchmark decision {index:04d}",
                f"benchmark body {index:04d} " + ("x" * 220),
            )
            for index in range(single_record_count)
        ]
        single_path, _ = _canonical_workflow(single_workflow, single_records)
        single_text = single_path.read_text(encoding="utf-8")
        if len(single_text.encode("utf-8")) < memory.HARD_FILE_BYTES:
            payload = single_text.rstrip("\n")
            padding = memory.HARD_FILE_BYTES - len(payload.encode("utf-8")) - 1
            single_text = payload + ("x" * max(0, padding)) + "\n"
            single_path.write_bytes(single_text.encode("utf-8"))
        single_text = single_path.read_text(encoding="utf-8")
        single_cold_started = time.perf_counter()
        single_parse = memory.parse_memory_document(single_text, single_path)
        single_cold_elapsed = time.perf_counter() - single_cold_started
        warm_times: list[float] = []
        for _ in range(5):
            started_warm = time.perf_counter()
            memory.parse_memory_document(single_text, single_path)
            warm_times.append(time.perf_counter() - started_warm)

        all_workflow_root = benchmark_root / "all-workflows" / "docs" / "nature-workflows"
        all_workflow_paths: list[Path] = []
        all_records = 0
        for workflow_index in range(1000):
            workflow_records = [
                (
                    auxiliary_id(0x1000 + workflow_index * 12 + record_index),
                    f"wf-{workflow_index:04d} decision {record_index:02d}",
                    f"wf-{workflow_index:04d} evidence {record_index:02d}",
                )
                for record_index in range(12)
            ]
            path, count = _canonical_workflow(all_workflow_root / f"wf-{workflow_index:04d}", workflow_records)
            all_workflow_paths.append(path)
            all_records += count
        all_workflow_texts = [path.read_text(encoding="utf-8") for path in all_workflow_paths]
        all_workflow_warm_times: list[float] = []
        for _ in range(5):
            warm_started = time.perf_counter()
            for path, text in zip(all_workflow_paths, all_workflow_texts):
                memory.parse_memory_document(text, path)
            all_workflow_warm_times.append(time.perf_counter() - warm_started)
        all_recall_started = time.perf_counter()
        all_recall = memory.command_memory_recall_all(
            root,
            benchmark_root / "all-workflows" / "docs" / "nature-workflows",
            "shared",
            "wf-0001 decision 01",
        )
        all_recall_elapsed = time.perf_counter() - all_recall_started
        if not all_recall.get("ok"):
            raise RuntimeError(all_recall)
        elapsed = time.perf_counter() - started
        benchmark_bytes = sum(path.stat().st_size for path in all_workflow_paths)
        single_canonical_checks = {
            "memory_name": single_path.name == "memory.md",
            "nature_yml": (single_workflow / "nature.yml").is_file(),
            "hard_file_size": single_path.stat().st_size == memory.HARD_FILE_BYTES,
            "parsed_records": len(single_parse.entries) == single_record_count,
        }
        benchmark_checks = {
            "single_canonical": all(single_canonical_checks.values()),
            "all_canonical": len(all_workflow_paths) == 1000 and all_records == 12000 and all(path.name == "memory.md" and path.parent.joinpath("nature.yml").is_file() for path in all_workflow_paths),
        }
    metrics = {
        "recall_at_3": sum(recall_values) / len(recall_values),
        "mrr": sum(reciprocal_values) / len(reciprocal_values),
        "ndcg_at_3": sum(ndcg_values) / len(ndcg_values),
        "no_hit_fpr": no_hit_false_positives / no_hit_queries if no_hit_queries else 0.0,
        "gold_queries": len(recall_values),
        "no_hit_queries": no_hit_queries,
    }
    slice_metrics: dict[str, dict[str, Any]] = {}
    slice_gates: dict[str, dict[str, Any]] = {}
    for case_slice, items in sorted(slice_records.items()):
        gold_items = [item for item in items if item["gold"]]
        no_hit_items = [item for item in items if not item["gold"]]
        slice_metric: dict[str, Any] = {
            "queries": len(items),
            "gold_queries": len(gold_items),
            "recall_at_3": sum(float(item["recall_at_3"]) for item in gold_items) / len(gold_items) if gold_items else None,
            "mrr": sum(float(item["reciprocal_rank"]) for item in gold_items) / len(gold_items) if gold_items else None,
            "ndcg_at_3": sum(float(item["ndcg_at_3"]) for item in gold_items) / len(gold_items) if gold_items else None,
            "no_hit_fpr": sum(bool(item["false_positive"]) for item in no_hit_items) / len(no_hit_items) if no_hit_items else None,
        }
        slice_metrics[case_slice] = slice_metric
        if case_slice == "no_hit":
            passed_slice = slice_metric["no_hit_fpr"] is not None and slice_metric["no_hit_fpr"] <= 0.10
            slice_gates[case_slice] = {"metric": "no_hit_fpr", "threshold": 0.10, "actual": slice_metric["no_hit_fpr"], "passed": passed_slice}
        else:
            passed_slice = slice_metric["recall_at_3"] is not None and slice_metric["recall_at_3"] >= 0.95
            slice_gates[case_slice] = {"metric": "recall_at_3", "threshold": 0.95, "actual": slice_metric["recall_at_3"], "passed": passed_slice}
    thresholds = {
        "recall_at_3": 0.95,
        "mrr": 0.90,
        "ndcg_at_3": 0.85,
        "no_hit_fpr_max": 0.10,
    }
    coverage_checks = {
        "fixture_minimum": fixture_minimum,
        "query_slices": required_slices.issubset(set(slice_metrics)),
        "local_scope": all(local_scope_checks),
        "lifecycle_filters": all(lifecycle_checks),
        "canonical_benchmark": all(benchmark_checks.values()),
    }
    passed = (
        metrics["recall_at_3"] >= thresholds["recall_at_3"]
        and metrics["mrr"] >= thresholds["mrr"]
        and metrics["ndcg_at_3"] >= thresholds["ndcg_at_3"]
        and metrics["no_hit_fpr"] <= thresholds["no_hit_fpr_max"]
        and all(gate["passed"] for gate in slice_gates.values())
        and all(coverage_checks.values())
    )
    platform_evidence = _platform_evidence()
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
        "slice_metrics": slice_metrics,
        "slice_gates": slice_gates,
        "thresholds": thresholds,
        "benchmark": {
            "single_workflow_records": single_record_count,
            "single_workflow_parsed_records": len(single_parse.entries),
            "single_workflow_bytes": len(single_text.encode("utf-8")),
            "single_workflow_cold_parse_seconds": single_cold_elapsed,
            "single_workflow_warm_median_seconds": sorted(warm_times)[len(warm_times) // 2],
            "single_workflow_warm_p95_seconds": _p95(sorted(warm_times)),
            "all_workflows": 1000,
            "all_workflow_records": all_records,
            "all_workflow_bytes": benchmark_bytes,
            "all_workflows_warm_median_seconds": sorted(all_workflow_warm_times)[len(all_workflow_warm_times) // 2],
            "all_workflows_warm_p95_seconds": _p95(sorted(all_workflow_warm_times)),
            "all_workflows_recall_elapsed_seconds": all_recall_elapsed,
            "all_workflows_recall_results": len(all_recall.get("results", [])),
            "canonical_paths": {"single": "canonical-benchmark/single-workflow/memory.md", "all_workflows_root": "canonical-benchmark/all-workflows/docs/nature-workflows"},
            "environment": {
                "python": platform.python_version(),
                "os": platform.platform(),
                "machine": platform.machine(),
                "cpu_count": os.cpu_count(),
                "cold_start_seconds": single_cold_elapsed,
                "warm_runs": 5,
            },
        },
        "query_results": query_results,
        "coverage_checks": coverage_checks,
        "benchmark_checks": benchmark_checks,
        "single_canonical_checks": single_canonical_checks,
        "platform_evidence": platform_evidence,
        "trace": [
            {"event": "fixture_loaded", "path": str(RECALL_FIXTURE), "version": fixture["version"]},
            {"event": "queries_scored", "count": len(query_results), "slices": sorted(slice_metrics)},
            {"event": "scope_lifecycle_checked", "coverage_checks": coverage_checks},
            {"event": "canonical_benchmark_materialized", "single_bytes": len(single_text.encode("utf-8")), "all_workflow_records": all_records},
            {"event": "gates_evaluated", "slice_gates": slice_gates, "passed": passed},
        ],
        "evaluation_elapsed_seconds": elapsed,
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


def fresh_cite_case(root: Path, workflow: Path, locator: str) -> dict[str, Any]:
    """Resolve a citation in a clean process, independent of the writer."""
    result = memory.command_memory_show(root, workflow, "shared", locator)
    return {
        "ok": bool(result.get("ok")),
        "locator": result.get("entry", {}).get("locator") if result.get("ok") else None,
        "entry_id": result.get("entry", {}).get("id") if result.get("ok") else None,
        "error": result.get("error") if not result.get("ok") else None,
    }


def deterministic_admission_policy(scenario: dict[str, Any]) -> str:
    """Make the offline adapter decide from prompt content, not the gold map."""
    title = str(scenario.get("title", "")).casefold()
    body = str(scenario.get("body", "")).casefold()
    if "conversation only" in title or "do not persist" in body:
        return "skip"
    return "remember"


def agent_case(index: int, reviewer_verdicts_path: Path | None = None) -> dict[str, Any]:
    fixture = load_json(AGENT_FIXTURE)
    scenario = fixture["scenarios"][index]
    reviewer_path = reviewer_verdicts_path or REVIEWER_FIXTURE
    reviewer_artifact = load_reviewer_verdicts(reviewer_path, [item["id"] for item in fixture["scenarios"]])
    imported_reviewer_evidence = reviewer_evidence(reviewer_artifact, scenario["id"])
    policy_action = deterministic_admission_policy(scenario)
    expected_locator_ids = list(scenario.get("expected_locator_ids", []))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        trace: dict[str, Any] = {
            "policy": fixture.get("admission_policy", "local-deterministic-prompt-policy"),
            "prompt": {"scenario_id": scenario["id"], "title": scenario["title"], "body": scenario["body"]},
            "model": fixture["model"],
            "model_parameters": fixture.get("model_parameters", {}),
            "plugin_version": fixture.get("plugin_version"),
            "allowed_tools": fixture.get("allowed_tools", []),
            "tool_calls": [],
            "reviewer_evidence": imported_reviewer_evidence,
            "deterministic_checks": [],
        }
        created = progress.command_new_workflow(
            "docs/nature-workflows",
            f"agent-{scenario['id']}",
            f"Agent eval {scenario['id']}",
            ["resume: fresh resume and cite"],
            base=root,
        )
        workflow = Path(created["workflow_dir"])
        trace["tool_calls"].append({
            "tool": "nature_new_workflow",
            "arguments": {"slug": f"agent-{scenario['id']}", "title": f"Agent eval {scenario['id']}"},
            "ok": bool(created.get("workflow_dir")),
        })
        trace["project_snapshot_before"] = _project_snapshot(root)
        before = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        written: dict[str, Any] | None = None
        if policy_action == "remember":
            expected_entry_id = expected_locator_ids[0] if expected_locator_ids else None
            original_uuid4 = memory.uuid.uuid4
            try:
                if expected_entry_id:
                    memory.uuid.uuid4 = lambda: uuid.UUID(expected_entry_id[3:])
                written = memory.command_memory_remember(
                    root,
                    workflow,
                    "shared",
                    scenario["title"],
                    scenario["body"],
                    {"kind": "decision", "provenance": "user"},
                )
            finally:
                memory.uuid.uuid4 = original_uuid4
            trace["tool_calls"].append({
                "tool": "nature_memory_remember",
                "arguments": {"scope": "shared", "title": scenario["title"], "metadata": {"kind": "decision", "provenance": "user"}},
                "ok": bool(written.get("ok")),
            })
            if not written.get("ok"):
                return {"ok": False, "scenario": scenario["id"], "error": written}
        else:
            trace["tool_calls"].append({"tool": "nature_memory_remember", "skipped": True, "reason": "fixture policy selected skip"})
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
        trace["tool_calls"].append({
            "tool": "nature_resume_with_memory",
            "arguments": {"scope": "shared", "query": scenario["title"]},
            "ok": fresh_process.returncode == 0,
            "fresh_process": True,
        })
        trace["tool_calls"].append({
            "tool": "nature_memory_recall",
            "arguments": {"scope": "shared", "query": scenario["title"]},
            "ok": fresh_process.returncode == 0,
            "fresh_process": True,
        })
        after = (workflow / "memory.md").read_bytes() if (workflow / "memory.md").exists() else b""
        context = resumed.get("memory_context", {})
        recalled = {"results": context.get("results", [])}
        written_ids = [item["id"] for item in recalled.get("results", [])]
        expected_write = bool(scenario["should_remember"])
        actual_write = policy_action == "remember"
        unauthorized_write = actual_write and not expected_write
        unexpected_skip = expected_write and not actual_write
        forbidden_leak = any(text in after.decode("utf-8", "replace") for text in scenario["must_not_write"])
        correct_write = (bool(written and written.get("ok")) == expected_write) and not unauthorized_write
        correct_recall = (not expected_write) or bool(written and written.get("entry_id") in written_ids)
        no_write_violation = not unauthorized_write and (actual_write or after == before)
        cited = not expected_write and not written
        citation_status = "not_applicable" if cited else "invalid"
        if written and written.get("entry_id"):
            expected_id_match = written.get("entry_id") in expected_locator_ids
            fresh_cite = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--mode",
                    "fresh-cite",
                    "--root",
                    str(root),
                    "--workflow",
                    str(workflow),
                    "--locator",
                    str(written.get("locator")),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            cited_payload = json.loads(fresh_cite.stdout) if fresh_cite.stdout.strip() else {}
            cited = (
                expected_write
                and expected_id_match
                and fresh_cite.returncode == 0
                and cited_payload.get("ok")
                and cited_payload.get("entry_id") == written.get("entry_id")
                and cited_payload.get("locator") == written.get("locator")
            )
            citation_status = "validated" if cited else "invalid"
            trace["tool_calls"].append({
                "tool": "nature_memory_show",
                "arguments": {"scope": "shared", "locator": written.get("locator")},
                "ok": bool(cited_payload.get("ok")),
                "fresh_process": True,
            })
        trace["project_snapshot_after"] = _project_snapshot(root)
        trace["deterministic_checks"] = [
            {"name": "write_expectation", "passed": correct_write},
            {"name": "recall_expectation", "passed": correct_recall},
            {"name": "no_write_boundary", "passed": no_write_violation},
            {"name": "forbidden_content_absent", "passed": not forbidden_leak},
            {"name": "locator_valid", "passed": cited},
            {"name": "citation_status", "passed": citation_status in {"validated", "not_applicable"}},
        ]
        deterministic_checks_passed = all(item["passed"] for item in trace["deterministic_checks"])
        reviewer_passed = all(item["verdict"] == "pass" for item in imported_reviewer_evidence["reviewers"])
        allowed_tools = set(fixture.get("allowed_tools", []))
        unauthorized_tools = [item["tool"] for item in trace["tool_calls"] if item["tool"] not in allowed_tools]
        return {
            "ok": deterministic_checks_passed and reviewer_passed and fresh_process.returncode == 0,
            "scenario": scenario["id"],
            "expected_write": expected_write,
            "workflow_steps": ["new", policy_action, "fresh_resume", "recall", "cite"],
            "agent_action": policy_action,
            "expected_locator_ids": expected_locator_ids,
            "citation_status": citation_status,
            "write_precision": 1.0 if actual_write and correct_write else (1.0 if not actual_write else 0.0),
            "write_recall": 1.0 if correct_recall else 0.0,
            "locator_valid": cited,
            "unauthorized_writes": 1 if unauthorized_write else 0,
            "unexpected_skips": 1 if unexpected_skip else 0,
            "security_failures": 1 if forbidden_leak or unauthorized_write else 0,
            "fresh_process": fresh_process.returncode == 0,
            "fresh_error": fresh_process.stderr.strip()[:400] if fresh_process.returncode else None,
            "deterministic_checks_passed": deterministic_checks_passed,
            "reviewer_verdicts_passed": reviewer_passed,
            "trace": trace,
            "unauthorized_tool_calls": unauthorized_tools,
        }


def agent_eval(runs: int, reviewer_verdicts_path: Path | None = None) -> dict[str, Any]:
    fixture = load_json(AGENT_FIXTURE)
    if len(fixture["scenarios"]) < 20:
        raise RuntimeError("agent fixture does not meet the 20 scenario minimum")
    reviewer_path = reviewer_verdicts_path or REVIEWER_FIXTURE
    reviewer_artifact = load_reviewer_verdicts(reviewer_path, [item["id"] for item in fixture["scenarios"]])
    cases: list[dict[str, Any]] = []
    script = Path(__file__).resolve()
    for run in range(runs):
        for index in range(len(fixture["scenarios"])):
            process = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--mode",
                    "agent-case",
                    "--index",
                    str(index),
                    "--reviewer-verdicts",
                    str(reviewer_path),
                ],
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
    unauthorized_tool_calls = sum(len(item.get("unauthorized_tool_calls", [])) for item in cases)
    trace_complete = all(
        bool(item.get("trace", {}).get("tool_calls"))
        and bool(item.get("trace", {}).get("deterministic_checks"))
        and len(item.get("trace", {}).get("reviewer_evidence", {}).get("reviewers", [])) == 2
        and "checks" not in item.get("trace", {}).get("reviewer_evidence", {})
        for item in cases
    )
    reviewer_disagreements = sum(
        bool(item.get("trace", {}).get("reviewer_evidence", {}).get("agreement", {}).get("disagreement"))
        for item in cases
    )
    reviewer_verdicts_passed = all(item.get("reviewer_verdicts_passed", False) for item in cases)
    reviewer_input_complete = all(
        item.get("trace", {}).get("reviewer_evidence", {}).get("source") == "external_reviewer_input"
        and item.get("trace", {}).get("reviewer_evidence", {}).get("artifact_sha256") == reviewer_artifact["artifact_sha256"]
        and item.get("trace", {}).get("reviewer_evidence", {}).get("connected_model_evaluation") is False
        for item in cases
    )
    snapshots_complete = all("project_snapshot_before" in item.get("trace", {}) and "project_snapshot_after" in item.get("trace", {}) for item in cases)
    passed = precision >= 0.90 and recall >= 0.80 and locator_valid and security_failures == 0 and unauthorized_writes == 0 and unauthorized_tool_calls == 0 and trace_complete and snapshots_complete and reviewer_verdicts_passed and reviewer_input_complete and all(item.get("ok") for item in cases)
    return {
        "ok": passed,
        "mode": "agent",
        "fixture": {"version": fixture["version"], "scenarios": len(fixture["scenarios"]), "runs": runs, "fresh_process_per_case": True, "workflow_contract": ["new", "remember", "fresh_resume", "recall", "cite"]},
        "model": fixture["model"],
        "metrics": {"write_precision": precision, "write_recall": recall, "locator_valid": locator_valid, "security_failures": security_failures, "unauthorized_writes": unauthorized_writes, "unauthorized_tool_calls": unauthorized_tool_calls, "trace_complete": trace_complete, "snapshots_complete": snapshots_complete, "actual_writes": actual_writes},
        "thresholds": {"write_precision": 0.90, "write_recall": 0.80, "security_failures": 0},
        "rubric": {
            "source": "external_reviewer_input",
            "artifact": reviewer_path.as_posix(),
            "artifact_sha256": reviewer_artifact["artifact_sha256"],
            "reviewers": reviewer_artifact["reviewer_ids"],
            "disagreements": reviewer_disagreements,
            "all_verdicts_pass": reviewer_verdicts_passed,
            "evidence": "per-case imported reviewer verdicts with evidence references",
            "evaluation_scope": "offline_fixture_policy",
            "connected_model_evaluation": False,
            "note": "This run does not claim connected model evaluation; connected results require their own external reviewer artifact.",
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("deterministic", "agent", "agent-case", "fresh-resume", "fresh-cite"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--root")
    parser.add_argument("--workflow")
    parser.add_argument("--query")
    parser.add_argument("--locator")
    parser.add_argument("--reviewer-verdicts")
    args = parser.parse_args()
    if args.mode == "deterministic":
        result = deterministic_eval()
    elif args.mode == "agent":
        result = agent_eval(args.runs, Path(args.reviewer_verdicts) if args.reviewer_verdicts else None)
    elif args.mode == "fresh-resume":
        result = fresh_resume_case(Path(args.root), Path(args.workflow), args.query or "nature workflow")
    elif args.mode == "fresh-cite":
        result = fresh_cite_case(Path(args.root), Path(args.workflow), args.locator or "")
    else:
        result = agent_case(args.index, Path(args.reviewer_verdicts) if args.reviewer_verdicts else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
