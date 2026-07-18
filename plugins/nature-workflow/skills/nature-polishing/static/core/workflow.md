# Polishing execution workflow

Use this execution layer together with `failure-modes.md`. It governs the optional persistent prose-profile path without changing ordinary polishing or layout-only work.

## 0. Classify prose versus layout

If the request changes only LaTeX placement or typesetting, use `references/latex-layout.md` and do not apply, generate, or audit a prose profile. Every workflow-bound layout-only task must call `nature_style_resolve` once with the exact task ID and `mode: layout-only`; this records a current-inventory exemption so completion does not demand a prose receipt. A canonical or semantically classified prose task cannot claim this exemption. Untracked layout-only work needs no style call.

Persistent profile creation is explicit only. Ordinary polishing, generic "Nature style", and one-turn concise/formal/natural requests create no profile. If the user explicitly asks to generate, learn, save, or update a reusable profile, hand that operation to `nature-prose-style` first.

## 1. Pin the workflow operation

For manuscript prose bound to a Nature workflow, pin the exact `project_root`, `workflow_dir`, task ID, section, normalized UTF-8 input source path, and final evidence path. Never select the latest workflow by recency. Convert PDF/DOCX with `nature-reader` (or the established extractor) and write pasted prose to a workflow-local `.md`/`.txt` source file before editing; the source must remain independently hashable after audit.

Call `nature_style_resolve` before rewriting:

- `not_configured` or `not_applicable`: keep the existing polishing path and create no receipt.
- `prose_style_choice_required`: stop, present the exact candidate profile IDs and scopes, and ask the user. Never rank, merge, fuzzy-match, or infer a choice.
- `resolved`: retain the workflow/task identity, profile and inventory ETags, selection mode/ETag, resolution ETag, section, and returned validated traits. If this was a one-turn choice, retain and pass the exact explicit profile ID to audit.
- invalid, stale, mismatched, or scope-conflicting state: fail visibly; do not silently fall back.

## 2. Diagnose before editing

Use `failure-modes.md` and the selected paper-type, section, journal, and language fragments to identify structural issues before sentence-level edits. Preserve the Terminology Ledger and surface missing content instead of inventing it.

## 3. Apply style below invariants

Apply only resolved traits whose scope includes `global` or the current section. The priority is:

`facts, evidence, citations, and ethics > explicit current-turn request > section and journal hard constraints > selected prose profile > skill defaults`

The profile cannot change numbers, units, statistics, citations, canonical terminology, causal direction, novelty, scope, limitations, or evidence strength. Skip any conflicting trait and record it in the style review.

## 4. Audit the exact final output

Only when resolution returned `resolved`, write the final polished prose to the pinned evidence path and perform the semantic style and content-invariant review. Call `nature_style_audit` on that exact file with the task ID, section, retained one-turn profile ID when applicable, profile ETag, resolution ETag, `operation: polishing`, `style_checks: passed`, `content_invariants: passed`, and the required normalized source path. The tool compares numeric tokens, measurements/units, and numeric citations deterministically.

Return the tool-created `style-receipts/<task-id>.json` path. Missing or stale receipts, changed output hashes, failed invariants, and unresolved profile choices block completion. Fix only style-safe issues and rerun the audit; never alter scientific content to satisfy style.
