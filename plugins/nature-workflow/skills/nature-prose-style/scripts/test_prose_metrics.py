#!/usr/bin/env python3
"""Tests for bounded, source-free prose metrics."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prose_metrics as metrics  # noqa: E402


class ProseMetricsTests(unittest.TestCase):
    def test_split_sections_handles_numbered_headings_and_exclusions(self) -> None:
        manuscript = """\
# Abstract

An abstract claim may indicate a bounded result.

# 1. Introduction

We introduce the question and its scientific context.

# 2. Methods

Samples were measured with a calibrated instrument.

| Group | Value |
| --- | --- |
| A | 42 |

# Acknowledgements

EXCLUDEDACKNOWLEDGEMENT must never be analyzed.

# References

EXCLUDEDREFERENCE must never be analyzed.
"""

        paragraphs = metrics.split_sections(manuscript)

        self.assertEqual(
            [item["scope"] for item in paragraphs],
            ["abstract", "intro", "methods"],
        )
        combined = " ".join(item["text"] for item in paragraphs)
        self.assertNotIn("EXCLUDEDACKNOWLEDGEMENT", combined)
        self.assertNotIn("EXCLUDEDREFERENCE", combined)
        self.assertNotIn("| Group |", combined)

    def test_figure_legends_use_a_separate_scope(self) -> None:
        manuscript = """\
# Results

The treatment increased the measured response.

Figure 1. Response distributions across the three conditions.

The secondary analysis suggests the same pattern.
"""

        paragraphs = metrics.split_sections(manuscript)

        self.assertEqual(
            [item["scope"] for item in paragraphs],
            ["results", "figure-legend", "results"],
        )
        self.assertEqual(paragraphs[1]["ref"], "figure-legend:p001")

    def test_table_captions_are_excluded_instead_of_becoming_figure_legends(self) -> None:
        manuscript = """\
# Results

The treatment increased the measured response.

Table 1. Response values for all experimental conditions.

Figure 2. Response distributions across conditions.
"""

        paragraphs = metrics.split_sections(manuscript)
        combined = " ".join(item["text"] for item in paragraphs)

        self.assertEqual(
            [item["scope"] for item in paragraphs],
            ["results", "figure-legend"],
        )
        self.assertNotIn("Table 1", combined)

    def test_stateful_non_prose_blocks_and_markdown_tables_are_skipped(self) -> None:
        manuscript = r"""# Introduction

Visible introduction prose remains available for analysis.

```python
# Results
FENCEDCODE must never be analyzed.
```

~~~text
TILDEFENCE must never be analyzed.
~~~

Before comment <!-- MULTILINECOMMENT
# Methods
still hidden --> after comment remains prose.

Before dollar math $$
DOLLARMATH must never be analyzed.
$$ after dollar math remains prose.

Before bracket math \[
BRACKETMATH must never be analyzed.
\] after bracket math remains prose.

Group | Value
--- | ---:
TABLEWITHOUTOUTERPIPE | 42

| Group | Value |
| :--- | ---: |
| TABLEWITHOUTERPIPE | 84 |

# Results

Visible result prose remains available for analysis.
"""

        paragraphs = metrics.split_sections(manuscript)
        combined = " ".join(item["text"] for item in paragraphs)

        self.assertEqual(paragraphs[-1]["scope"], "results")
        self.assertTrue(all(item["scope"] == "intro" for item in paragraphs[:-1]))
        for excluded in (
            "FENCEDCODE",
            "TILDEFENCE",
            "MULTILINECOMMENT",
            "DOLLARMATH",
            "BRACKETMATH",
            "TABLEWITHOUTOUTERPIPE",
            "TABLEWITHOUTERPIPE",
        ):
            self.assertNotIn(excluded, combined)
        for visible in (
            "Before comment",
            "after comment remains prose.",
            "Before dollar math",
            "after dollar math remains prose.",
            "Before bracket math",
            "after bracket math remains prose.",
        ):
            self.assertIn(visible, combined)

    def test_analysis_contains_metrics_but_no_source_prose(self) -> None:
        unique_source = "QUASARPROVENANCE must remain confined to the source manuscript."
        manuscript = f"# Discussion\n\n{unique_source}\n"

        result = metrics.analyze(manuscript, holdout_ratio=0)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)

        self.assertNotIn("QUASARPROVENANCE", serialized)
        self.assertNotIn(unique_source, serialized)
        self.assertNotIn('"text"', serialized)
        self.assertRegex(
            result["source_fingerprint"], r"^sha256:[0-9a-f]{64}$"
        )
        self.assertEqual(result["global"]["paragraphs"], 1)
        self.assertEqual(result["sections"]["discussion"]["paragraphs"], 1)

    def test_holdout_partition_is_stable_and_complete(self) -> None:
        results = [
            f"Paragraph {index} reports a measured response and may indicate a stable pattern."
            for index in range(1, 21)
        ]
        discussion = [
            f"Discussion paragraph {index} explains a distinct scientific implication."
            for index in range(1, 11)
        ]
        manuscript = (
            "# Abstract\n\nA single abstract paragraph remains in training.\n\n"
            "# Results\n\n"
            + "\n\n".join(results)
            + "\n\n# Discussion\n\n"
            + "\n\n".join(discussion)
            + "\n"
        )

        first = metrics.analyze(manuscript, holdout_ratio=0.35, seed="stable-seed")
        second = metrics.analyze(manuscript, holdout_ratio=0.35, seed="stable-seed")

        self.assertEqual(first, second)
        analyzed = set(first["analyzed_refs"])
        held_out = set(first["holdout_refs"])
        expected = {item["ref"] for item in metrics.split_sections(manuscript)}
        self.assertTrue(analyzed)
        self.assertTrue(held_out)
        self.assertTrue(analyzed.isdisjoint(held_out))
        self.assertEqual(
            {locator.removeprefix("train:") for locator in analyzed}
            | {locator.removeprefix("holdout:") for locator in held_out},
            expected,
        )
        self.assertEqual(
            sum(locator.startswith("holdout:results:") for locator in held_out), 7
        )
        self.assertEqual(
            sum(locator.startswith("holdout:discussion:") for locator in held_out), 4
        )
        self.assertNotIn("holdout:abstract:p001", held_out)
        self.assertIn("train:abstract:p001", analyzed)

    def test_every_scope_retains_training_at_high_holdout_ratio(self) -> None:
        manuscript = """\
# Abstract

One abstract paragraph.

# Introduction

First introduction paragraph.

Second introduction paragraph.

# Results

First result paragraph.

Second result paragraph.

Third result paragraph.
"""

        result = metrics.analyze(manuscript, holdout_ratio=0.99, seed="bounded")

        for scope in ("abstract", "intro", "results"):
            self.assertTrue(
                any(ref.startswith(f"train:{scope}:") for ref in result["analyzed_refs"])
            )

    def test_output_locators_are_canonical_and_source_free(self) -> None:
        manuscript = "# Results\n\n" + "\n\n".join(
            f"Canonical locator paragraph {index}." for index in range(1, 9)
        )

        result = metrics.analyze(manuscript, holdout_ratio=0.5, seed="canonical")
        payload = json.dumps(result, ensure_ascii=False)

        for locator in result["analyzed_refs"]:
            self.assertRegex(locator, r"^train:[a-z][a-z-]*:p\d{3}$")
        for locator in result["holdout_refs"]:
            self.assertRegex(locator, r"^holdout:[a-z][a-z-]*:p\d{3}$")
        self.assertNotIn("Canonical locator paragraph", payload)

    def test_zero_holdout_analyzes_every_paragraph(self) -> None:
        manuscript = """\
# Introduction

We define the scientific question.

# Results

The measurements suggest a reproducible response.
"""

        result = metrics.analyze(manuscript, holdout_ratio=0)

        self.assertEqual(result["holdout_refs"], [])
        self.assertEqual(len(result["analyzed_refs"]), 2)
        self.assertEqual(result["global"]["paragraphs"], 2)

    def test_source_fingerprint_normalizes_line_endings(self) -> None:
        lf = "# Results\n\nThe measurements indicate a stable response.\n"
        crlf = lf.replace("\n", "\r\n")

        self.assertEqual(
            metrics.analyze(lf)["source_fingerprint"],
            metrics.analyze(crlf)["source_fingerprint"],
        )

    def test_invalid_holdout_ratio_and_empty_manuscript_fail(self) -> None:
        for ratio in (-0.01, 1.0):
            with self.subTest(ratio=ratio), self.assertRaises(ValueError):
                metrics.analyze("# Results\n\nSome prose.\n", holdout_ratio=ratio)
        with self.assertRaises(ValueError):
            metrics.analyze("# References\n\n[1] Excluded source.\n")


if __name__ == "__main__":
    unittest.main()
