---
name: nature-cover-letter
description: >-
  Draft a target-journal-specific Cover Letter for a Nature-family or other high-impact
  manuscript submission, using the polished manuscript, target-journal study notes, journal
  selection report, and figure-permission status. Produce a Word `.docx` Cover Letter with a
  fixed seven-paragraph structure and a nine-item submission-declaration checklist, using only
  project-confirmed facts and marking everything else as a placeholder or `需要用户确认`. Use
  when the user asks to write a cover letter, 投稿信, Cover Letter 撰写, 投稿附信, submission
  letter, editor letter, declaration/statement letter, 投稿声明, 附信, or needs the letter that
  accompanies a manuscript submission. Also trigger on general submission-letter needs during
  academic writing even without the word "Nature", such as writing a cover letter for any
  journal, drafting a submission letter, an editor letter for a paper, and Chinese phrasings
  like 写投稿信、投稿信撰写、给编辑的信、附信撰写、投稿说明信、cover letter 定制、投稿声明核查、
  投稿信定制、期刊投稿信.
metadata:
  version: 0.1.0
  author: Fused from SCI 0-1 step 18 (Cover Letter Writer), refactored into static/dynamic layers
---

# Nature Cover Letter — Router

This skill is one atomic step delegated by **nature-orchestrator**. The orchestrator
`start`s the `coverletter` step, hands you the manuscript and target-journal context, and
after you return a deliverable it will `complete` the step with `--evidence <path to your
Cover_Letter.docx>`. Your job is to produce that Word deliverable and its declaration checklist.

This skill is split into two layers:

- A **static layer** under `static/` that holds versioned, reusable content fragments (the
  default stance and red lines, the drafting workflow, and the deliverable/structure contract).
- A **dynamic layer** (this file plus `manifest.yaml`) that loads the core every time.

Do not apply the cover-letter logic from memory or from this router, and do not do the
domain reasoning yourself from recollection. Always load the fragments from disk, and verify
dynamic facts (target-journal Cover Letter requirements, declaration rules, permission status)
live rather than recalling them.

## Routing protocol

Follow these three steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). Then read every file listed under `always_load`:

- `static/core/stance.md` — what the letter is for, the default stance, and the red lines
  (no fabrication, no exaggeration, no review-as-original-research framing).
- `static/core/workflow.md` — accepted inputs, the numbered workflow, and the output format.
- `static/core/output-contract.md` — the deliverable list, the fixed seven-paragraph
  structure, the nine-item declaration checklist, and the Word delivery requirement.
- `../_shared/core/ethics.md` — the shared citation/ethics/AI red line inherited by every
  nature-* step.

### 2. Run the workflow

Follow `core/workflow.md`: confirm inputs and mode, verify the target journal's current Cover
Letter requirements online, extract manuscript facts and the nine declaration items, list what
the user must confirm, draft the seven-paragraph letter from confirmed facts only, fill the
declaration checklist, run QA, and render the final `Cover_Letter.docx`.

Use only project-confirmed information. Anything missing is a placeholder or `需要用户确认`;
never fabricate author, affiliation, corresponding-author, funding, ethics, conflict-of-interest,
data-availability, AI-use, or figure/table-permission facts. Do not hide unresolved
figure-permission risks. Markdown is a support draft only — the `.docx` is the deliverable.

### 3. Return the deliverable as evidence

End by naming the absolute path of `Cover_Letter.docx` (plus the declaration checklist) so the
orchestrator can `complete` the step with it as evidence. Report package readiness:
`ready_to_submit`, `draft_with_placeholders`, `needs_user_confirmation`, or `blocked`.

## Why this split

- The static layer is versioned and reviewable; the core stays small for a normal run.
- The router is short on purpose. Update fragments, not this file, when adding scope.
- This structure mirrors `nature-response`, `nature-data`, `nature-writing`, and the other
  nature-* atomic skills.
