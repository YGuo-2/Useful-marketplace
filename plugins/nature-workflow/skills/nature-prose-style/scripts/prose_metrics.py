#!/usr/bin/env python3
"""Extract bounded, source-free prose metrics from a sectioned English manuscript."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


SECTION_ALIASES = {
    "abstract": "abstract",
    "introduction": "intro",
    "background": "intro",
    "related work": "related-work",
    "materials and methods": "methods",
    "materials & methods": "methods",
    "methods": "methods",
    "methodology": "methods",
    "results": "results",
    "experiments": "experiments",
    "discussion": "discussion",
    "results and discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
}
EXCLUDED_SECTIONS = {
    "acknowledgement",
    "acknowledgements",
    "acknowledgment",
    "acknowledgments",
    "author contributions",
    "competing interests",
    "conflict of interest",
    "data availability",
    "funding",
    "references",
    "bibliography",
    "supplementary information",
}
HEADING_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s+)?(?:\d+(?:\.\d+)*[.)]?\s+)?"
    r"(?P<title>[A-Za-z][A-Za-z &/-]{1,80})\s*$"
)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])" )
WORD_RE = re.compile(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b")
CAPTION_ID = r"(?:S?\d+[A-Za-z]?|[A-Za-z]{1,3}\d+|[A-Z])"
FIGURE_LEGEND_RE = re.compile(rf"^fig(?:ure)?\.?\s*{CAPTION_ID}\b", re.IGNORECASE)
TABLE_CAPTION_RE = re.compile(rf"^table\s*{CAPTION_ID}\b", re.IGNORECASE)
HEDGES = {"appear", "appears", "could", "indicate", "indicates", "likely", "may", "might", "possible", "possibly", "suggest", "suggests"}
BOOSTERS = {"clearly", "demonstrate", "demonstrates", "establish", "establishes", "prove", "proves", "robustly", "strongly"}
CONNECTIVES = {
    "accordingly",
    "although",
    "because",
    "consequently",
    "conversely",
    "furthermore",
    "however",
    "moreover",
    "nevertheless",
    "therefore",
    "thus",
    "whereas",
}
PASSIVE_RE = re.compile(r"\b(?:am|are|is|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en)\b", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s{0,3}(?P<fence>`{3,}|~{3,}).*$")
TABLE_DELIMITER_CELL_RE = re.compile(r"^\s*:?-{3,}:?\s*$")


def _percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return float(ordered[index])


def _section_name(line: str) -> tuple[str | None, bool]:
    match = HEADING_RE.match(line)
    if not match:
        return None, False
    title = re.sub(r"\s+", " ", match.group("title").strip().lower())
    title = re.sub(r"^\d+(?:\.\d+)*\s*", "", title)
    if title in EXCLUDED_SECTIONS:
        return title, True
    return SECTION_ALIASES.get(title), False


def _drop_non_prose(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or bool(re.fullmatch(r"[-=:|\s]{3,}", stripped))
    )


def _strip_non_prose_blocks(lines: list[str]) -> list[str]:
    """Remove stateful Markdown blocks while preserving prose outside inline spans."""
    cleaned: list[str] = []
    span_state: str | None = None
    fence_char: str | None = None
    fence_length = 0
    closing_tokens = {
        "html": "-->",
        "dollar-math": "$$",
        "bracket-math": r"\]",
    }
    opening_tokens = {
        "html": "<!--",
        "dollar-math": "$$",
        "bracket-math": r"\[",
    }

    for line in lines:
        if fence_char is not None:
            closing_fence = re.compile(
                rf"^\s{{0,3}}{re.escape(fence_char)}{{{fence_length},}}\s*$"
            )
            if closing_fence.match(line):
                fence_char = None
                fence_length = 0
            cleaned.append("")
            continue

        if span_state is None:
            fence_match = FENCE_RE.match(line)
            if fence_match:
                fence = fence_match.group("fence")
                fence_char = fence[0]
                fence_length = len(fence)
                cleaned.append("")
                continue

        cursor = 0
        prose_parts: list[str] = []
        while cursor < len(line):
            if span_state is not None:
                closing = closing_tokens[span_state]
                closing_index = line.find(closing, cursor)
                if closing_index < 0:
                    cursor = len(line)
                    break
                cursor = closing_index + len(closing)
                span_state = None
                continue

            candidates = [
                (line.find(token, cursor), state, token)
                for state, token in opening_tokens.items()
                if line.find(token, cursor) >= 0
            ]
            if not candidates:
                prose_parts.append(line[cursor:])
                break
            opening_index, state, opening = min(candidates, key=lambda item: item[0])
            prose_parts.append(line[cursor:opening_index])
            cursor = opening_index + len(opening)
            span_state = state

        cleaned.append("".join(prose_parts))
    return cleaned


def _is_table_delimiter(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = stripped.strip("|").split("|")
    return len(cells) >= 2 and all(TABLE_DELIMITER_CELL_RE.fullmatch(cell) for cell in cells)


def _markdown_table_rows(lines: list[str]) -> set[int]:
    """Return physical line indexes belonging to Markdown pipe tables."""
    table_rows: set[int] = set()
    for index, line in enumerate(lines):
        if not _is_table_delimiter(line) or index == 0:
            continue
        header = lines[index - 1]
        if not header.strip() or "|" not in header:
            continue
        table_rows.update((index - 1, index))
        cursor = index + 1
        while cursor < len(lines):
            row = lines[cursor]
            if not row.strip() or "|" not in row:
                break
            table_rows.add(cursor)
            cursor += 1
    return table_rows


def split_sections(text: str) -> list[dict[str, Any]]:
    current = "global"
    excluded = False
    buffer: list[str] = []
    paragraphs: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    def flush() -> None:
        nonlocal buffer
        paragraph = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer = []
        if not paragraph or excluded:
            return
        if TABLE_CAPTION_RE.match(paragraph):
            return
        scope = "figure-legend" if FIGURE_LEGEND_RE.match(paragraph) else current
        counts[scope] += 1
        paragraphs.append(
            {"scope": scope, "ref": f"{scope}:p{counts[scope]:03d}", "text": paragraph}
        )

    normalized_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines = _strip_non_prose_blocks(normalized_lines)
    table_rows = _markdown_table_rows(cleaned_lines)
    for index, raw in enumerate(cleaned_lines):
        section, is_excluded = _section_name(raw)
        if section is not None or is_excluded:
            flush()
            current = section or "excluded"
            excluded = is_excluded
            continue
        if not raw.strip():
            flush()
            continue
        if excluded or index in table_rows or _drop_non_prose(raw):
            flush()
            continue
        buffer.append(raw)
    flush()
    return paragraphs


def _holdout_refs(
    paragraphs: list[dict[str, Any]], seed: str, ratio: float
) -> set[str]:
    """Select a deterministic, bounded holdout independently within each scope."""
    if ratio == 0:
        return set()
    by_scope: dict[str, list[dict[str, Any]]] = {}
    for item in paragraphs:
        by_scope.setdefault(item["scope"], []).append(item)

    selected: set[str] = set()
    for scope, items in sorted(by_scope.items()):
        target = min(len(items) - 1, math.floor(len(items) * ratio + 0.5))
        if target <= 0:
            continue

        def rank(item: dict[str, Any]) -> tuple[bytes, str]:
            digest = hashlib.sha256(
                f"{seed}\0{scope}\0{item['ref']}".encode("utf-8")
            ).digest()
            return digest, item["ref"]

        selected.update(item["ref"] for item in sorted(items, key=rank)[:target])
    return selected


def _metrics(paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    sentence_lengths: list[int] = []
    paragraph_lengths: list[int] = []
    words: list[str] = []
    passive_count = 0
    punctuation = Counter()
    for item in paragraphs:
        text = item["text"]
        paragraph_words = WORD_RE.findall(text)
        paragraph_lengths.append(len(paragraph_words))
        words.extend(word.lower() for word in paragraph_words)
        for sentence in SENTENCE_RE.split(text):
            length = len(WORD_RE.findall(sentence))
            if length:
                sentence_lengths.append(length)
        passive_count += len(PASSIVE_RE.findall(text))
        punctuation.update({"em_dash": text.count("—"), "semicolon": text.count(";"), "colon": text.count(":")})
    word_counts = Counter(words)
    total_words = max(len(words), 1)

    def per_1000(tokens: set[str]) -> float:
        return round(sum(word_counts[token] for token in tokens) * 1000 / total_words, 3)

    return {
        "paragraphs": len(paragraphs),
        "sentences": len(sentence_lengths),
        "words": len(words),
        "sentence_words": {
            "mean": round(statistics.fmean(sentence_lengths), 3) if sentence_lengths else 0.0,
            "median": round(statistics.median(sentence_lengths), 3) if sentence_lengths else 0.0,
            "p90": round(_percentile(sentence_lengths, 0.9), 3),
        },
        "paragraph_words": {
            "mean": round(statistics.fmean(paragraph_lengths), 3) if paragraph_lengths else 0.0,
            "median": round(statistics.median(paragraph_lengths), 3) if paragraph_lengths else 0.0,
        },
        "first_person_we_per_1000": round((word_counts["we"] + word_counts["our"] + word_counts["ours"]) * 1000 / total_words, 3),
        "passive_markers_per_1000": round(passive_count * 1000 / total_words, 3),
        "hedges_per_1000": per_1000(HEDGES),
        "boosters_per_1000": per_1000(BOOSTERS),
        "connectives_per_1000": per_1000(CONNECTIVES),
        "punctuation": dict(punctuation),
    }


def analyze(text: str, *, holdout_ratio: float = 0.2, seed: str | None = None) -> dict[str, Any]:
    if not 0 <= holdout_ratio < 1:
        raise ValueError("holdout_ratio must be in [0, 1)")
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = split_sections(normalized_text)
    if not paragraphs:
        raise ValueError("no manuscript prose was found")
    source_bytes = normalized_text.encode("utf-8")
    source_fingerprint = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    holdout_seed = seed if seed is not None else source_fingerprint
    held_out_refs = _holdout_refs(paragraphs, holdout_seed, holdout_ratio)
    analyzed = [item for item in paragraphs if item["ref"] not in held_out_refs]
    holdout = [item for item in paragraphs if item["ref"] in held_out_refs]
    by_scope: dict[str, list[dict[str, Any]]] = {}
    for item in analyzed:
        by_scope.setdefault(item["scope"], []).append(item)
    return {
        "schema_version": 1,
        "source_fingerprint": source_fingerprint,
        "holdout_ratio": holdout_ratio,
        "holdout_refs": [f"holdout:{item['ref']}" for item in holdout],
        "analyzed_refs": [f"train:{item['ref']}" for item in analyzed],
        "global": _metrics(analyzed),
        "sections": {scope: _metrics(items) for scope, items in sorted(by_scope.items())},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract source-free prose metrics from a manuscript.")
    parser.add_argument("input", help="UTF-8 Markdown or plain-text manuscript.")
    parser.add_argument("--holdout-ratio", type=float, default=0.2)
    parser.add_argument("--seed", default=None, help="Optional holdout seed; defaults to the source fingerprint.")
    parser.add_argument("--output", default="", help="Optional JSON output path; stdout is always written.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.input)
    result = analyze(source.read_text(encoding="utf-8"), holdout_ratio=args.holdout_ratio, seed=args.seed)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8", newline="")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
