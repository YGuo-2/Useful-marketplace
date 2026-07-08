---
name: nature-journal
description: >-
  Select tiered target journals for a completed Nature-family manuscript draft, then deep-learn the
  confirmed journal's recent high-quality output to build a submission-adaptation standard. Given a
  full draft, match candidate journals with journal-finder tools, verify each on official sources
  (journal site, Author Guidelines, JCR quartile, CAS partition, impact factor, CiteScore, APC, OA,
  review timeline, indexing, whether the article type is accepted), score fit on 14 dimensions, run a
  submission-risk checklist, and stratify into Tier 1 / Tier 2 / Tier 3 / Backup. After the user
  confirms a journal, study its recent 3-5 year articles across 8 style dimensions and its hard
  submission requirements. Use this skill whenever the user asks to choose a target journal, pick
  where to submit, compare candidate journals, learn a journal's style/author guidelines, or says
  "选刊", "目标期刊选择", "选目标期刊", "投哪个期刊", "期刊匹配", "分梯队选刊", "冲刺/主投/稳妥/保底",
  "投稿风险核查", "期刊风格学习", "作者指南核查", "对标期刊学习", "投稿格式适配".
metadata:
  version: 0.1.0
  author: Fused from SCI steps 14 (target-journal selector) + 15 (target-journal deep learner)
---

# Nature Journal — Router

This skill is an **atomic step delegated by `nature-orchestrator`**. The orchestrator `start`s this
step, you run the workflow, and it `complete`s the step with `--evidence <your report path>`. It is
also the **decision fork** for journal choice: you produce tiered candidates, the orchestrator
presents them under its decision protocol, and only after the user confirms a journal do you run the
deep-learning half.

This skill is split into two layers:

- A **static layer** under `static/` that holds the versioned domain logic (stance and red lines, the
  numbered workflow, and the output contract).
- A **dynamic layer** (this file plus `manifest.yaml`) that loads the core every time.

Do not apply the selection or style-learning logic from memory or from this router. Journal metrics,
scope, APC, and submission rules are dynamic; always load fragments from disk and verify journal facts
online at use time.

## Routing protocol

Follow these steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `../_shared/core/ethics.md` — the ethics and citation red lines every nature-* skill inherits.
- `static/core/stance.md` — purpose, default stance, mandatory-online-verification rule, source
  hierarchy, and the red lines that apply to every journal job.
- `static/core/workflow.md` — the numbered selection-then-deep-learning workflow and each step's
  deliverable, including the 14-dimension fit score, four-tier strategy, and 13-item risk checklist.
- `static/core/output-contract.md` — the exact deliverable files, field specs, report templates, and
  the evidence-path report format.

### 2. No content axis — read the manuscript profile and preferences inline

Like the other linear nature-* skills, nature-journal has no fragment axis. Its variation is runtime
parameters, not different content bodies:

- **manuscript profile** — topic, discipline, article type, target readership, novelty, evidence
  strength, figure/table completeness. Extract from the supplied full draft.
- **user targets** — target partition (JCR Q1/Q2…, CAS Zone 1/2…), OA/APC tolerance, publisher or
  timeline preferences, any journals the user already favors.
- **stage** — `select` (produce tiered candidates) vs `deep-learn` (study the confirmed journal). Run
  `select` first; only enter `deep-learn` after the user confirms a journal.

If the full draft or the target partition/preferences are missing, ask for them before searching.

### 3. Run the workflow

Follow `core/workflow.md`. Verify every journal fact online — journal-finder tools first for matching,
then official sources for confirmation — and mark anything unconfirmable as `需要人工核查`. Never let a
high-risk, non-matching, or non-type-accepting journal be the top recommendation. Deliver tiered
candidates as `select` evidence; after confirmation deliver the journal-adaptation standard as
`deep-learn` evidence, per `core/output-contract.md`.

### 4. Reach for references only when needed

Open `references.on_demand` files only when a step needs them — e.g. the genre taxonomy to judge
whether a journal accepts the manuscript's article type.

## Why this split

- The static layer is versioned and reviewable; the core carries all domain logic.
- The router is short on purpose. Update fragments, not this file, when adding scope.
- This structure mirrors `nature-citation`, `nature-response`, and the other linear nature-* skills.
