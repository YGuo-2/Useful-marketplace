# Prose-profile workflow

Run this workflow for persistent profile generation, update, and calibration. Use the state tools for inventory changes; do not hand-edit the `prose_style` object in `nature.yml`.

## 1. Pass the persistence gate

Confirm that the user explicitly requested a reusable profile or explicitly asked to keep using the style of specified source material. If the request is ordinary prose work, generic Nature style, a simple tone adjective, or a one-time imitation that should not be saved, stop this workflow and create no persistent artifact.

## 2. Pin the workflow and profile identity

Require explicit `project_root` and `workflow_dir`. Select or create a profile ID matching `[a-z][a-z0-9-]{0,63}`. Do not derive a sensitive title or author name into the ID unless the user chose it.

Before writing, inspect the explicit workflow's `prose-profiles/` directory and registered style summary to see whether the ID already exists. Treat replacement as an update, not an accidental new profile. `nature_style_index` manages the project bootstrap; it does not list profiles.

## 3. Acquire and label source material

Prefer a complete English manuscript written by the author before submission. Accept multiple comparable English articles when provided.

- For PDF, DOI, arXiv, or publisher HTML, hand extraction and section reconstruction to `nature-reader`, then consume its structured output.
- For Markdown or pasted text, build the same section map locally.
- Record `author-draft`, `author-journal-mixed`, `reference-paper`, `journal-corpus`, or `explicit-preferences` provenance before analysis.
- Hash the normalized source and retain only the fingerprint plus abstract source locators in the profile.

Never bypass a paywall or upload unpublished or sensitive manuscripts to an unapproved external service.

## 4. Normalize sections and isolate non-prose material

Identify Abstract, Introduction, Methods, Results, Discussion, Conclusion, and figure legends where present. Exclude references, acknowledgements, author metadata, tables, equations, code, and supplementary boilerplate from prose-style inference. Analyze figure legends as scope `figure-legend` and never blend them into body-prose statistics. Normalize Introduction to `intro`; use only the scopes allowed by the output contract.

If section detection is unreliable, record the uncertainty and avoid section overrides rather than guessing.

## 5. Build a deterministic holdout

Stratify eligible paragraphs by section and reserve approximately 20 percent as a holdout before trait extraction. Derive the split deterministically from the source fingerprint so repeated runs use the same paragraphs. Never use holdout paragraphs as evidence for profile traits.

If the source is too short to support both analysis and holdout, generate only a low-confidence draft and ask for more source material; do not register it.

## 6. Extract stable differential traits

Follow `references/profile-generation.md`.

1. Run deterministic surface metrics where available.
2. Analyze discourse moves by section.
3. Compare observed patterns with the Nature workflow defaults.
4. Keep only repeated, actionable differences with source locators.
5. Put weak or conflicting observations under uncertainty, not in active traits.

Aim for 8-12 high-value rules when the evidence supports them; the schema permits 1-12. Use the canonical trait names and preferred values from the reference. Never encode a source sentence as a trait value.

## 7. Write an unregistered draft

Write `prose-profiles/<profile-id>.md` according to `static/core/output-contract.md`, with `status: draft`. The machine block must contain only the documented schema and abstract values. Human-readable evidence summaries outside the block are non-executable.

Do not add a draft to the workflow inventory and do not install a project bootstrap.

## 8. Validate, promote, and register

Run `nature_style_validate` against the profile document. On failure, leave it as `draft` or mark it `invalid`, report the exact issue, and do not register it.

On success:

1. change the document status to `ready`;
2. run validation again after the status change;
3. call `nature_style_register`;
4. inspect `nature_style_register`'s returned selection state and inventory ETag.

Registration of the first usable profile must produce `auto_single` and make it available to downstream writing and polishing immediately. It also installs or repairs the fixed project bootstrap through the state tool. Do not write the bootstrap manually.

When registration creates two or more usable profiles, the inventory must become `needs_choice`. Prompt immediately with each profile's ID, provenance, and scopes; use `nature_style_select` without a section for a persistent default, with a concrete section for a persistent section binding, or pass an exact ID only for the current resolution when the user requests a one-turn choice. Do not start prose work until the relevant choice is settled.

## 9. Optionally calibrate with the holdout

Calibration improves a profile but is not required before use.

1. Produce two versions of the same holdout content: workflow defaults and profile-guided prose.
2. Preserve facts, numbers, citations, terminology, and claim strength exactly.
3. Randomize labels so the user does not know which version uses the profile.
4. Ask which is closer to the intended voice and which dimensions are off.
5. Revise only the implicated traits; do not regenerate the whole profile blindly.
6. Set `status: calibrated`, update the separate calibration record and profile timestamp, validate, and register again.

Write the optional calibration record to `style-calibration/<profile-id>.md`. Do not include full source articles.

## 10. Preserve selection and ETag semantics

Any profile or inventory mutation changes its ETag. Never reuse a receipt or resolver result from an earlier ETag. A new second profile, update, disable, deletion, invalid profile, or incompatible scope may invalidate the saved selection; honor `needs_choice` or the tool error and ask instead of guessing.

## 11. Hand off to the prose execution chain

For the next draft or polish, pass the explicit workflow and task/section context to `nature-writing` or `nature-polishing`. Those consumers must resolve the profile before generating prose, audit the actual output afterward, and retain the resulting receipt before a guarded prose task is completed.
