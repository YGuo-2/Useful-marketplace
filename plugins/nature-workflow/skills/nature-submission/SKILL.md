---
name: nature-submission
description: >-
  Assemble the final submission package for a Nature-family manuscript and walk the author
  through the target journal's submission system. Use when the user is ready to submit, asks to
  prepare submission materials, build the final material checklist, plan file naming and upload
  order, get submission-system field suggestions, run a missing-material and risk check, produce a
  pre-submit confirmation checklist, or record a post-submission handoff. Covers Main Manuscript,
  Title Page, Cover Letter, Figures, Tables, Graphical Abstract, Highlights, Supplementary
  Materials, Declarations, Funding, Data Availability, AI Use statement, Figure Permissions, and
  Suggested/Opposed Reviewers. Also trigger on general journal-submission needs even without the
  word "Nature", such as preparing to submit a paper to any journal, organizing files for an
  editorial-manager / ScholarOne / Editorial Manager system, and Chinese phrasings like 投稿指导、
  投稿材料准备、投稿清单、提交投稿、投稿系统填写、上传顺序、文件命名、投稿前检查、投稿风险核查、
  最终提交前确认、投稿后记录、准备投稿、怎么投稿、投稿流程.
metadata:
  version: 0.1.0
  author: Useful-marketplace, fusing SCI从0-1workflow step 19 (SCI投稿指导器) into nature-workflow
---

# Nature Submission — Router

This skill is one **atomic step** delegated by `nature-orchestrator`. The orchestrator `start`s
this step, waits for the deliverable, then `complete`s it with `--evidence <deliverable path>`.
Produce a real file and return its absolute path so it can serve as evidence.

This skill is split into two layers:

- A **static layer** under `static/` that holds versioned, reusable content fragments (the default
  stance and red lines, the submission workflow, and the output contract).
- A **dynamic layer** (this file plus `manifest.yaml`) that loads the core every time.

Do not apply the submission logic from memory or from this router. Do not run any domain reasoning
from memory. Always load fragments from disk as described below.

## Routing protocol

Follow these steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `static/core/stance.md` — the purpose, the default stance, the submission-system **security red
  lines** (the most important section), mandatory online verification, and the source hierarchy.
- `static/core/workflow.md` — accepted inputs, the numbered workflow, and each step's product.
- `static/core/output-contract.md` — the deliverable package, filename rules, the pre-submit
  confirmation checklist, and the delivery format (`.docx` main, Markdown supporting).
- `../_shared/core/ethics.md` — the citation, authorship, and AI red lines that bind every step.

### 2. No content axis — identify inputs and language inline

Like `nature-response` and `nature-citation`, this skill has no fragment axis. Its variation is
runtime parameters, not different content bodies:

- **available materials** — which of the manuscript, figures, cover letter, declarations, and
  permission records already exist.
- **target journal** — the submission system, article type, and author guidelines to verify online.
- **user language** — if the user writes Chinese, return the Chinese report and reminders.

State in one short line which materials are present and which target journal was detected before
building the checklist.

### 3. Verify online, then run the workflow

Submission systems and author guidelines change. **Verify the target journal's current submission
requirements online before finalizing.** Mark anything unverifiable as `需要人工核查`. Never state
journal scope, article-type rules, file-format limits, APC, or license terms from memory.

Follow the numbered workflow in `core/workflow.md`: gather materials, verify guidelines online,
build the material checklist, plan file naming and upload order, draft submission-system field
suggestions, run the missing-material and risk check, produce the pre-submit confirmation
checklist, and assemble the `.docx` deliverable plus its post-submission record template.

### 4. Respect the security boundary

Follow the submission-system security red lines in `core/stance.md` at all times: you may guide and
prepare field content, but you must never request or store account credentials, never bypass
captcha / two-factor / institutional authentication, never confirm payment or copyright transfer or
legal declarations on the user's behalf, and never click Submit before the user's final
confirmation.

## Why this split

- The static layer is versioned and reviewable; the core carries all domain logic.
- The router stays short on purpose. Update the core fragments, not this file, when adding scope.
- This structure mirrors `nature-response`, `nature-citation`, and the other nature-* skills.
