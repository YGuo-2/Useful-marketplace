---
name: nature-topic
description: >-
  Analyze the exported RIS/reference records from a literature search — year, title, and abstract fields —
  to derive review-topic candidates and identify research gaps from real literature patterns rather than
  keyword imagination. Cluster the export, surface crowded themes, emerging mechanisms, contradictions, and
  under-synthesized gaps, then produce three candidate topics (稳妥 / 平衡 / 高冲击) with one recommended
  option for the orchestrator's decision protocol. Use this skill whenever the user asks to choose a review
  topic, compare research gaps, cluster a literature export, or turn a search result into writable angles,
  and for Chinese phrasings like 选题、研究空白、研究空白识别、综述选题、候选选题、选题分析、
  文献聚类、主题聚类、研究热点、研究方向、确定选题、RIS 年份标题摘要分析、选题与研究空白识别.
metadata:
  version: 0.1.0
  author: nature-workflow, fused from SCI 04-SCI选题与研究空白识别
---

# Nature Topic & Research-Gap — Router

This skill is one **atomic step delegated by `nature-orchestrator`**. The orchestrator `start`s this step,
expects a real deliverable, and then runs `complete <task_id> --evidence <product-path>`. Produce a file it
can pass as evidence.

Do not run the topic logic from memory or from this router. Always load the fragments from disk first.

## Routing protocol

Follow these four steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `static/core/stance.md` — what this step produces, the fixed topic pattern, and the prohibited moves / red lines.
- `static/core/workflow.md` — the numbered steps and the product each step must leave behind.
- `static/core/output-contract.md` — the required deliverable and its decision-ready structure.
- `../_shared/core/ethics.md` — the citation and fabrication red lines shared across nature-* skills.

### 2. Confirm inputs inline

Detect the inputs before analyzing; this step has no content axis, only runtime parameters:

- **exported records** — the RIS / reference records from the upstream search step, plus any search/export log. If the export is missing, say so and route back rather than inventing records.
- **research context** — research direction, keywords, and target partition (分区) if provided. Ask only for the smallest missing item and record it.
- **user language** — return the analysis notes in the user's language; keep topic titles bilingual (中文选题 + English draft title).

State the detected inputs in one short line before analyzing.

### 3. Run the workflow

Follow the steps in `core/workflow.md`: inspect year/title/abstract, build the analysis table, cluster,
compare gaps, and derive three candidate topics along 稳妥/平衡/高冲击 with one recommended option. This is
a **decision step**: emit all candidates for the orchestrator to present under its decision protocol; do not
silently pick one.

Never invent specific papers, authors, DOI, PMID, journal statistics, or citation counts. Mark incomplete
metadata `需要人工核查`. This is topic analysis, not formal screening — do not claim a final number of
included studies. Do not assert dynamic journal facts (分区 / IF / scope / APC / submission or licensing
rules) from memory; verify online or flag them.

### 4. Reach for references only when needed

The files under `references.on_demand` in the manifest are deep references, not defaults — open them only
when their condition applies (consistent term forms across candidates, or framing a candidate's review
angle / paper type).

## Why this split

- The static core carries all domain logic; the router stays short and cheap per invocation.
- Update the fragments, not this file, when adding scope.
- This structure mirrors `nature-citation`, `nature-data`, and the other atomic nature-* steps.
