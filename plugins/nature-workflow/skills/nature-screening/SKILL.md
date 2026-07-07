---
name: nature-screening
description: >-
  Screen, deduplicate, relevance-rank, and classify an exported literature corpus into a
  Zotero-ready review library for any discipline. Use when a user has raw bibliographic exports
  (RIS/NBIB/BIB/CSV/TXT from PubMed, Web of Science, Scopus, or another database) plus a confirmed
  review topic and wants to remove duplicates, rank records by title/abstract topic match, keep the
  top strongly-relevant records, build a second-level/third-level category tree, and produce an
  import mapping for a reference manager. Discipline-agnostic: medicine, life sciences, engineering,
  materials, chemistry, physics, computer science, environmental science, agriculture, management,
  social science, and interdisciplinary work are all in scope. Also trigger on general review-prep
  needs even without the word "Nature", such as building a review literature library, organizing a
  search export before full-text reading, deduplicating references, or Chinese phrasings like
  文献筛选、文献去重、相关性排序、文献分类、综述文献库、二级三级分类、Zotero导入分类、
  保留强相关文献、筛掉不相关文献、建综述文献库、文献治理.
metadata:
  version: 0.1.0
  author: Useful-marketplace, fusing SCI从0-1workflow step 06 into nature-workflow
---

# Nature Screening — Router

This skill is an **atomic step** in the nature-* collection. `nature-orchestrator` delegates the
"screen and classify the literature corpus" step to it: the orchestrator `start`s the step, this
skill runs the workflow and writes real deliverable files, and the orchestrator then `complete`s the
step with `--evidence <deliverable path>`. It can also run standalone when a user just wants to
screen and classify an export.

Do not screen, deduplicate, or classify from memory or from this router. The domain logic lives on
disk. Load it every time as described below.

## Routing protocol

Follow these steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `static/core/stance.md` — what the screening package is, the discipline-agnostic stance, the
  source hierarchy, and the prohibited actions / red lines.
- `static/core/workflow.md` — the numbered screening workflow and the concrete file each step emits.
- `static/core/output-contract.md` — the deliverable file set, the folder tree, and the user-facing
  report format.
- `../_shared/core/ethics.md` — the shared citation/ethics boundary that constrains every nature-*
  skill.

### 2. Confirm inputs and scope inline

This skill has no content axis; its variation is runtime parameters, stated in one short line before
you start:

- **discipline** — the user's field (medicine / engineering / materials / CS / environment / …). It
  decides which field-specific objects count as "core"; never force biomedical labels onto a
  non-biomedical topic.
- **confirmed review topic and framework** — the topic, research gap, and benchmark-review writing
  framework that define the title/abstract matching criteria.
- **export inputs** — the raw record files and their formats. If exports or a confirmed topic are
  missing, say which single upstream item is needed instead of guessing.

### 3. Run the workflow

Follow the numbered steps in `core/workflow.md`: inventory inputs without modifying them, normalize
metadata, deduplicate conservatively, set discipline-specific matching criteria, rank by relevance,
retain the top strongly-relevant records, build the second/third-level classification, assign every
record, prepare the reference-manager import mapping, and write the logs and quality checks. Deliver
exactly the files in `core/output-contract.md` and report their absolute paths so a caller can use
one as `--evidence`.

Never fabricate DOIs, PMIDs, authors, journals, or metadata; mark unverifiable items
`需要人工核查`. Verify any dynamic fact (journal scope, impact factor, quartile, APC, submission or
licence rules) online — do not answer those from memory.

### 4. Reach for references only when needed

Anything under `references/` (if present) is a deep reference, not a default. Open it on demand per
the `references.on_demand` table in the manifest, not on every run.

## Why this split

- The static core is versioned and reviewable; it stays small for a normal screening run.
- The router is short on purpose. Update the core fragments, not this file, when adding scope.
- This structure mirrors `nature-citation`, `nature-data`, and the other linear nature-* skills.
