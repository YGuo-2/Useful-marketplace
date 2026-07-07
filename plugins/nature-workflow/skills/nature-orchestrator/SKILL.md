---
name: nature-orchestrator
description: Drive a full manuscript lifecycle from topic to submission by turning a genre template into a deterministic task sequence and delegating each step to the right nature-* skill. Use when the user wants to write a whole paper or review from scratch, be walked through the end-to-end workflow, or resume a manuscript-wide project rather than run a single isolated skill. Trigger on end-to-end framings such as "从头写一篇论文/综述", "带我走完整个流程", "论文从0到1", "投稿全流程", "orchestrate a manuscript", "paper workflow from topic to submission". For a single, isolated task (only draft an abstract, only make a figure, only verify a citation) route directly to that nature-* skill instead.
metadata:
  version: 0.1.0
  author: Useful-marketplace, fusing SCI从0-1workflow orchestration into nature-workflow
---

# Nature Manuscript Orchestrator — Router

This skill is the **lifecycle orchestrator** for the nature-* collection. It does
not do the domain work itself. It turns a **genre template** into an ordered task
sequence in the state engine, then walks the user step by step, **delegating each
step to the nature-* skill (or new tail-chain skill) that owns it**.

Two hard boundaries define what this skill is:

- It **orchestrates**, it does not re-implement. Search, reading, figures, drafting,
  polishing, and reviewer response already have deep implementations in the
  nature-* skills. This skill delegates to them; it never inlines their prompts.
- The **state engine holds the truth**. Progress, the active step, and the "next
  step" are computed by `nature_progress.py`, not narrated from memory. Do not
  hand-maintain a progress block; call the engine and read back its output.

Do not apply orchestration logic from memory. Load fragments from disk as below.

## Routing protocol

Follow these steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). It declares the `paper_type` axis, its allowed
values, and the template file each value maps to. Read every file under
`always_load`: the shared paper-type taxonomy and ethics, plus this skill's
`core/stance.md`, `core/workflow.md`, and `core/decision.md`.

### 2. Detect or ask the genre (paper_type)

Decide the `paper_type` from the user's framing using the taxonomy in
`../_shared/core/paper-type-taxonomy.md` (research / methods / hypothesis /
algorithmic / review). State the detected genre in one short line so the user can
correct it cheaply. If only the `review` template exists in the manifest and the
user needs another genre, say so — do not force a review flow onto a research paper.

### 3. Load the genre template

Read the fragment mapped for the detected genre, e.g.
`static/fragments/paper_type/review.md`. It gives the **ordered task sequence**:
each step's `id: title`, which skill owns it (delegate target), what `evidence` a
completed step should record, and which steps are decision forks.

### 4. Seed the workflow (once)

If no workflow exists yet, initialize the whole sequence in the state engine in a
single call — the template is the task list. See `core/workflow.md` for the exact
`nature_new_workflow` / CLI call. Do not create tasks one at a time; the template
seeds them all at `new`.

### 5. Walk the sequence

Loop the drive cycle in `core/workflow.md`: read `status` to find the next task →
`start` it → **delegate to the owning skill** (tell the user which nature-* skill
runs this step, or run it if it is you) → on a real deliverable, `complete` it with
an `evidence` path → if stuck, `block` it with a reason. At decision forks, apply
the lightweight option protocol in `core/decision.md`. Surface progress by echoing
the engine's `status`/`progress.md`, never by reciting step numbers from memory.

## Why this shape

- The genre template is versioned data. Adding a genre or a step is one fragment
  edit, not code.
- The engine gives a code-observable flow for free: ordered steps, a single active
  task, an evidence gate on completion, and a resumable record — replacing the
  hand-written progress block and the unobservable quality gate of the old prose
  pipeline.
- The router stays short. Update fragments and `core/*`, not this file, when adding
  scope.
