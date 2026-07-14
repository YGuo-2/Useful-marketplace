#!/usr/bin/env python3
"""Deterministic recall tests for the Nature memory engine."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nature_memory  # noqa: E402


def make_workflow(base: Path, slug: str = "wf") -> Path:
    workflow_dir = base / "docs" / "nature-workflows" / slug
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "nature.yml").write_text('{"schema_version":1}\n', encoding="utf-8")
    return workflow_dir


def remember(workspace: Path, workflow: Path, title: str, body: str, **metadata: object) -> dict:
    payload = {"kind": "decision", "provenance": "user"}
    payload.update(metadata)
    result = nature_memory.command_memory_remember(
        workspace, workflow, "shared", title, body, payload
    )
    if not result["ok"]:
        raise AssertionError(result)
    return result


class NatureMemoryRecallTests(unittest.TestCase):
    def test_exact_title_and_id_rank_before_lexical_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            workflow = make_workflow(workspace)
            exact = remember(workspace, workflow, "引用风格", "RIS 导出与 EndNote 兼容")
            remember(workspace, workflow, "引用工具", "引用风格需要人工核对")
            remember(workspace, workflow, "格式记录", "EndNote 兼容格式")

            by_title = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "引用风格"
            )
            self.assertTrue(by_title["ok"], by_title)
            self.assertEqual(by_title["results"][0]["id"], exact["entry_id"])
            self.assertIn("引用风格", by_title["results"][0]["matched_terms"])

            by_id = nature_memory.command_memory_recall(
                workspace, workflow, "shared", exact["entry_id"]
            )
            self.assertEqual(by_id["results"][0]["id"], exact["entry_id"])
            self.assertGreater(by_id["results"][0]["score"], by_title["results"][0]["score"] - 1)

    def test_nfkc_english_tokens_and_cjk_bigrams_are_explainable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            workflow = make_workflow(workspace)
            english = remember(workspace, workflow, "BM25 baseline", "The retrieval baseline is deterministic")
            chinese = remember(workspace, workflow, "中文召回策略", "采用中文双字词召回")

            english_result = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "ＢＭ25"
            )
            self.assertEqual(english_result["results"][0]["id"], english["entry_id"])
            self.assertIn("bm25", english_result["results"][0]["matched_terms"])

            chinese_result = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "召回策略"
            )
            self.assertEqual(chinese_result["results"][0]["id"], chinese["entry_id"])
            self.assertTrue({"召回", "回策", "策略"}.intersection(chinese_result["results"][0]["matched_terms"]))

    def test_filters_apply_before_scoring_and_scope_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            workflow = make_workflow(workspace)
            active = remember(workspace, workflow, "共享约束", "active body", kind="constraint")
            archived = remember(workspace, workflow, "历史约束", "archived body", kind="constraint")
            nature_memory.command_memory_forget(
                workspace,
                workflow,
                "shared",
                archived["entry_id"],
                archived["etag"],
                "obsolete",
            )
            local_path = workflow / "memory.local.md"
            local_path.write_text(
                nature_memory.serialize_entry(
                    "本地约束",
                    "private body",
                    {
                        "schema": 1,
                        "id": "nm_1234567890ab4cde8f0123456789abcd",
                        "kind": "constraint",
                        "lifecycle": "active",
                        "provenance": "user",
                        "created_at": "2026-07-14T07:00:00Z",
                        "updated_at": "2026-07-14T07:00:00Z",
                    },
                ),
                encoding="utf-8",
            )

            default = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "约束"
            )
            self.assertEqual([item["id"] for item in default["results"]], [active["entry_id"]])
            self.assertNotIn("private body", json.dumps(default, ensure_ascii=False))

            archived_result = nature_memory.command_memory_recall(
                workspace,
                workflow,
                "shared",
                "约束",
                filters={"lifecycle": "archived", "kind": "constraint"},
            )
            self.assertEqual([item["id"] for item in archived_result["results"]], [archived["entry_id"]])

            local_result = nature_memory.command_memory_recall(
                workspace, workflow, "local", "本地约束"
            )
            self.assertEqual(local_result["results"][0]["title"], "本地约束")

    def test_top_k_is_bounded_zero_score_is_empty_and_order_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            workflow = make_workflow(workspace)
            for index in range(6):
                remember(workspace, workflow, f"相同主题{index}", "同一正文")

            first = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "同一", top_k=5
            )
            second = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "同一", top_k=5
            )
            self.assertEqual(len(first["results"]), 5)
            self.assertEqual([item["id"] for item in first["results"]], [item["id"] for item in second["results"]])

            empty = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "完全无匹配词"
            )
            self.assertTrue(empty["ok"], empty)
            self.assertEqual(empty["results"], [])

            invalid = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "同一", top_k=6
            )
            self.assertFalse(invalid["ok"])
            self.assertEqual(invalid["error"]["code"], "invalid_top_k")

    def test_response_budget_keeps_records_complete_and_under_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            workflow = make_workflow(workspace)
            remember(workspace, workflow, "预算标题", "完整正文 " + ("x" * 500))

            result = nature_memory.command_memory_recall(
                workspace, workflow, "shared", "预算标题", max_bytes=900
            )
            serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.assertLessEqual(len(serialized), 900)
            if result["results"]:
                self.assertEqual(result["results"][0]["body"], "完整正文 " + ("x" * 500))


if __name__ == "__main__":
    unittest.main()
