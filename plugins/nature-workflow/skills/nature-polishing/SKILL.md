---
name: nature-polishing
description: Polish, restructure, translate, or proofread academic and scientific manuscript prose into publication-quality Nature-leaning English. Use for paragraphs, abstracts, introductions, results, discussions, conclusions, titles, methods, full manuscripts, and Chinese or English drafts; trigger on academic/scientific/SCI/paper writing, language editing, 学术写作、科研写作、论文润色、写paper、SCI写作、英文论文润色、语言润色、润色、改写、学术英语、英文写作. Also use for LaTeX layout/typesetting (排版) problems such as sparse pages, stranded headings, split or undersized figures, "Float too large", multi-panel arrangement, or sparse Supplementary Information. If the user explicitly asks to generate, learn, save, or reuse a persistent 文风画像, route that profile operation through nature-prose-style before polishing. Generic Nature style and one-turn concise/formal/natural requests remain ordinary polishing and never create a profile.
metadata:
  version: 6.2.0
  author: Yuan1z skill, refactored into static/dynamic layers
---

# Nature-Style Academic Polishing — Router

This skill is split into two layers:

- A **static layer** under `static/` that holds versioned, reusable content fragments (core principles, paper-type playbooks, per-section guidance, language-specific rules, per-journal style).
- A **dynamic layer** (this file plus `manifest.yaml`) that detects the request's axes and loads only the fragments needed for the current job.

Do not try to apply the polishing logic from memory or from this router. Always load fragments from disk as described below.

## Routing protocol

Follow these five steps every time the skill is invoked.

### 1. Load the manifest and the core layer

Read [manifest.yaml](manifest.yaml). It declares the axes (`paper_type`, `section`, `language`, `journal`), the allowed values, and the file paths each value maps to.

Also read every file listed under `always_load`. These hold the default stance, failure-mode diagnosis, ethics, execution workflow, output format, and optional prose-profile contract that apply to every polish job.

### 2. Detect the axis values for this request

For each axis in the manifest, decide the value using the manifest's `detect:` hint and the user's input:

- `paper_type` — research / methods / hypothesis / algorithmic / review. Default: research.
- `section` — abstract / intro / results / discussion / conclusion / title / methods. May be multiple. Ask the user if it is ambiguous and matters for the polish.
- `language` — en or zh-to-en. Detect from the draft itself.
- `journal` — nature / nat-comms / generic. Default: generic. If the user names a Nature subjournal, treat it as `nature`.

State the detected axis values in one short line to the user before proceeding, so they can correct you cheaply.

### 3. Load the matching fragments

For each axis value, Read the file mapped in the manifest. Skip the `section` axis only if the user has supplied free-floating prose with no section context.

Do **not** read every fragment in `static/`. Load only what step 2 selected.

### 4. Resolve optional persistent prose style, then polish

Persistent profile creation is an explicit opt-in. If the user asks to generate, learn, save, or update a reusable 文风画像, hand that operation to `nature-prose-style` first. Do not create a profile for ordinary polishing, generic "Nature style", or a one-turn request to be concise, formal, or natural.

For manuscript prose bound to a Nature workflow, follow `core/workflow.md`: normalize PDF/DOCX/pasted input to a separate UTF-8 source file, pin the exact project, workflow, task, section, source, and final evidence path, then call `nature_style_resolve` before rewriting. Continue unchanged on `not_configured` or `not_applicable`; stop and ask on `prose_style_choice_required`; apply only returned validated traits on `resolved`; and fail visibly on invalid, stale, or mismatched state. Never discover a workflow by recency or guess among profiles.

Apply the loaded fragments in this priority order, matching the `paper type -> section job -> paragraph logic -> claim/evidence/boundary -> sentence polish` rule from `core/failure-modes.md`:

1. Facts, evidence, citations, ethics, and the user's current-turn instructions.
2. Paper-type playbook (architecture, writing order).
3. Section-specific job and failure modes.
4. Journal hard constraints and language-specific rules.
5. The selected prose profile, when resolved, as a soft style layer above skill defaults.

If a paragraph's structural problem cannot be fixed without inventing content, flag it instead of papering over it.

When the resolver returned `resolved`, write the final polished prose to the pinned evidence path, perform the semantic style and invariant review, and call `nature_style_audit` on that exact file with `operation: polishing`, explicit `style_checks: passed` and `content_invariants: passed`, the required normalized source path, and the retained one-turn profile ID when applicable. Return the tool-created receipt path. Never audit an intermediate draft or hand-author a receipt.

### 5. Reach for references only when needed

The files under `references/` are deep references, not defaults. Open them on demand per the `references.on_demand` table in the manifest, for example when the user explicitly asks for phrasebank-style alternatives or a stricter style audit.

**Layout/typesetting (排版) requests are different.** If the user asks to fix
*placement* rather than wording — loose/sparse pages, stranded headings, figures
that don't fill the page or split across pages, "Float too large", multi-panel
arrangement, sparse Supplementary Information — skip the prose axes (paper_type,
section, language, journal), the prose-style resolver, and the style audit; load
`references/latex-layout.md` directly. Layout-only work never creates or consumes a
prose profile and never needs a style receipt, but workflow-bound layout work still
records a resolver exemption and prose-classified tasks cannot use it. The reference is self-contained: it
carries the diagnosis workflow (render → contact-sheet →
read the log), the float-glue and `[H]`/`\clearpage`/`placeins` patterns, and the
"regenerate wide figures taller at the source" rule. Always compile and visually
inspect rendered pages before and after — never judge layout from the `.tex` alone.

## Why this split

- The static layer is versioned and reviewable. Adding a new journal style or paper type is one new file plus one manifest line.
- The dynamic layer keeps each invocation cheap: only the fragments relevant to this draft enter context, instead of the full 1000-line monolith.
- The router itself is short on purpose. Update fragments, not this file, when adding scope.
