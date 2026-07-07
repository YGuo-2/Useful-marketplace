---
name: nature-benchmark
description: >-
  Build a benchmark review-corpus for a confirmed review topic and deep-learn it: from the upstream
  screened literature library, select the ~10 best-matching, highest journal-impact / highest-quality
  reviews, rank them by topical fit first then journal/article quality, build a benchmark review library
  and import it into Zotero (plugin/connector first, Computer Use fallback, then a manual boxed prompt),
  read only the PDFs the user actually obtained, and learn their framework, narrative logic, writing
  style, and figure layout to produce a classification guide for the downstream screening step. Use this
  skill for review (综述) manuscripts when the user says "建立综述对标库", "对标综述库", "对标综述",
  "综述对标库并深度学习", "对标文献库", "learn benchmark reviews", "综述框架学习", "标杆综述", "对标库",
  or needs a benchmark corpus + 二级/三级分类指导框架 before literature screening.
metadata:
  version: 0.1.0
  author: Nature workflow, fused from SCI stage 05 into static/dynamic layers
---

# Nature Benchmark — Router

This skill is one **atomic step delegated by `nature-orchestrator`** (review genre, Phase 3, step
`benchmark`). The orchestrator `start`s this step, hands you the step brief, and after you finish it
`complete`s the step with `--evidence <your artifact path>`. Produce a concrete artifact path that can
serve as that evidence.

This skill is split into two layers:

- A **static layer** under `static/` that holds versioned, reusable content fragments (the default stance
  and red lines, the benchmark-and-deep-learning workflow, and the output contract).
- A **dynamic layer** (this file plus `manifest.yaml`) that loads the core every time.

Do not apply the benchmark logic from memory or from this router, and do not invent journal metrics,
DOIs, or Zotero state. Always load fragments from disk as described below.

## Routing protocol

Follow these four steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `static/core/stance.md` — the purpose, the default stance, the red lines / Prohibited list, and the
  source hierarchy that apply to every benchmark job.
- `static/core/workflow.md` — the ordered steps, the artifact each step writes, and the Zotero / PDF /
  deep-reading handoffs.
- `static/core/output-contract.md` — the deliverable list, the RIS + report formats, and the quality gates.
- `../_shared/core/ethics.md` — the shared citation, attribution, and AI red lines (learn structure, never
  copy).

### 2. No content axis — confirm scope and inputs inline

nature-benchmark has no fragment axis. Its variation is runtime parameters, not different content bodies:

- **upstream inputs** — the screened/exported literature library and the confirmed review topic + research
  gap from the earlier steps. If either is missing, say so and route back rather than guessing.
- **Zotero state** — remind the user to open Zotero and keep it open through import, PDF acquisition, and
  PDF inspection.
- **PDF availability** — full-text deep learning runs only over PDFs the user has actually obtained; wait
  for the user's reply before reading.

State the detected inputs and how many suitable reviews you can reach in one short line before ranking.

### 3. Run the workflow

Follow the numbered steps in `core/workflow.md`: identify reviews in the upstream library, rank them
(topical fit first, then journal/article quality), select ~10 (record the max available and the reason if
fewer), generate the ranking table + selection rationale, export the benchmark RIS, import into Zotero via
the plugin/connector → Computer Use → manual boxed prompt priority, wait for the user's PDF acquisition
reply, deep-read only obtained PDFs, and convert the learning into the downstream classification guide.

Verify dynamic journal metrics (IF / quartile / CiteScore / APC / scope) live; mark anything unverifiable
as `需要人工核查`. Never claim to have read a PDF you did not read.

### 4. Report with evidence paths

Return the ranking table, the deep-learning conclusions, and the classification guide, and put the
benchmark-corpus report + classification-guide file paths where the orchestrator can record them as
`--evidence`. The full delivery format is in `core/output-contract.md`.

## Why this split

- The static layer is versioned and reviewable; the core stays small for a normal run.
- The router itself is short on purpose. Update fragments, not this file, when adding scope.
- This structure mirrors `nature-citation`, `nature-response`, `nature-data`, and the other nature-* atomic
  skills the orchestrator delegates to.
