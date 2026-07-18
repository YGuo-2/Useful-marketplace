---
name: nature-writing
description: Draft, restructure, or plan Nature-style manuscript sections from author-provided claims, results, figures, notes, or Chinese drafts. Use when the user wants to write or rebuild an abstract, introduction, related-work, method, experiments, discussion, conclusion, title, or full manuscript argument rather than only polish finished prose. Also trigger on general academic-writing requests even without the word "Nature", such as writing a paper from scratch, drafting a manuscript/section, structuring a paper, and Chinese phrasings like 学术写作、科研写作、论文写作、写论文、写paper、SCI写作、帮我写论文、搭论文框架、起草论文、写引言/摘要/讨论. If the user explicitly asks to generate, save, or reuse a persistent 文风画像, route that profile operation through nature-prose-style before drafting; generic Nature style or a one-turn concise/formal/natural request remains ordinary writing and must not create a profile.
metadata:
  version: 1.1.0
  author: Community contribution, refactored into static/dynamic layers
---

# Nature-Style Scientific Writing — Router

This skill is split into two layers:

- A **static layer** under `static/` that holds versioned, reusable content fragments (core stance + workflow, paper-type playbooks, per-section drafting guidance, language-specific rules, per-journal style).
- A **dynamic layer** (this file plus `manifest.yaml`) that detects the request's axes and loads only the fragments needed for the current job.

Do not try to apply the drafting logic from memory or from this router. Always load fragments from disk as described below.

## Routing protocol

Follow these five steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). It declares the axes (`paper_type`, `section`, `language`, `journal`), the allowed values, and the file paths each value maps to.

Also read every file listed under `always_load`. These hold the default stance, writing workflow, output format, and optional prose-profile execution contract that apply to every drafting job.

### 2. Detect the axis values for this request

For each axis in the manifest, decide the value using the manifest's `detect:` hint and the user's input:

- `paper_type` — research / methods / hypothesis / algorithmic / review. Default: research.
- `section` — abstract / intro / related-work / method / experiments / discussion / conclusion / title. May be multiple. Ask the user if it is ambiguous and matters for the draft.
- `language` — en or zh-to-en. Detect from the user's notes themselves.
- `journal` — nature / nat-comms / generic. Default: generic. If the user names a Nature subjournal, treat it as `nature`.

State the detected axis values in one short line to the user before drafting, so they can correct you cheaply.

### 3. Load the matching fragments

For each axis value, Read the file mapped in the manifest. Skip the `section` axis only when the user has explicitly asked for a free-floating argument paragraph with no section context.

Do **not** read every fragment in `static/`. Load only what step 2 selected.

### 4. Resolve optional persistent prose style, then draft

Persistent profile creation is an explicit opt-in. If the user asks to generate, learn, save, or update a reusable 文风画像, hand that operation to `nature-prose-style` first. Do not create a profile for ordinary drafting, generic "Nature style", or a one-turn request to be concise, formal, or natural.

For manuscript prose bound to a Nature workflow, follow the preflight in `core/workflow.md` before generating text. Pin the exact `project_root`, `workflow_dir`, task ID, section, and final evidence path; never guess the latest workflow. Call `nature_style_resolve` and handle its result exactly:

- `not_configured` or `not_applicable` — keep the existing drafting path and create no receipt.
- `prose_style_choice_required` — stop before drafting, show the exact candidate IDs and scopes, and ask the user. Never rank, merge, fuzzy-match, or infer a choice.
- `resolved` — apply only the returned validated traits for the current section; retain the selection mode, every returned ETag, and the exact profile ID for a one-turn audit.
- invalid, stale, mismatched, or scope-conflicting state — fail visibly; do not silently fall back.

If the task is not bound to an explicit workflow and the user did not name an existing paper-scoped profile, continue with ordinary writing. Do not discover or select a workflow by recency.

Apply the loaded fragments in this priority order:

1. Facts, evidence, citations, ethics, and the user's current-turn instructions.
2. Core stance + intake (`core/stance.md`) — surface missing claim / evidence / boundary before drafting.
3. Paper-type playbook and section-specific structure.
4. Journal hard constraints and language-specific rules.
5. The selected prose profile, when resolved, as a soft style layer above skill defaults.

Run the workflow in `core/workflow.md` end-to-end. Do not skip steps 1-3 (planning) just because the user asked for prose immediately — write the one-sentence argument first. A profile may change voice and rhythm, but never facts, numbers, citations, terminology, causal direction, scope, limitations, or evidence strength.

If essential evidence or boundary is missing, write a placeholder and list it under `Assumptions or missing inputs:` instead of inventing content.

When the resolver returned `resolved`, write the final prose to the pinned evidence path, perform the semantic style and invariant review, and call `nature_style_audit` against that exact file with `operation: writing`, explicit `style_checks: passed` and `content_invariants: passed`, and the retained one-turn profile ID when applicable. Return the tool-created receipt path with the output. Do not hand-author or reuse receipts.

### 5. Reach for references only when needed

The files under `references/` are deep references and the example library, not defaults. Open them on demand per the `references.on_demand` table in the manifest. Typical triggers:

- The user asks for a concrete example or template → `references/examples/index.md`.
- A section's draft has structural problems that the section fragment alone does not explain → the matching `references/<section>.md`.
- The user needs a broad-audience `Nature` abstract opening or asks about a `summary paragraph` → `references/nature-summary-paragraph.md`.
- The user asks "does this paragraph flow?" → `references/paragraph-flow.md`.
- The user asks for a self-review or rejection-risk audit → `references/paper-review.md`.

## Why this split

- The static layer is versioned and reviewable. Adding a new journal style, paper type, or section is one new file plus one manifest line.
- The dynamic layer keeps each invocation cheap: only the fragments relevant to this draft enter context, instead of the full multi-thousand-line reference set.
- The router itself is short on purpose. Update fragments, not this file, when adding scope.
- This structure mirrors `nature-polishing`, and shared content lives in the `_shared/` layer (see `manifest.yaml`, which references `../_shared/core/`) used by both skills.
