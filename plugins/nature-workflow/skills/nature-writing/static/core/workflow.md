# Writing workflow

Run these steps for any drafting or restructuring task. Steps 1-3 are planning, step 3b is an alignment gate, 4-6 are drafting, 7-8 are checking, step 9 is the revision loop.

## 0. Resolve optional persistent prose style

Profile creation is never implicit. Ordinary writing, generic "Nature style", and one-turn requests to be concise, formal, or natural stay on the existing path and create no profile. If the user explicitly asks to generate or save a reusable profile, hand that operation to `nature-prose-style` before drafting.

For prose bound to an explicit Nature workflow, pin `project_root`, `workflow_dir`, task ID, section, and final evidence path, then call `nature_style_resolve` before generating prose. Continue unchanged on `not_configured` or `not_applicable`. On `prose_style_choice_required`, stop and ask the user to choose from the exact profile IDs and scopes. On `resolved`, retain the profile and inventory ETags, selection mode/ETag, resolution ETag, and validated traits returned for this section. Retain the exact explicit profile ID for a one-turn choice and pass it to audit. Invalid, stale, or mismatched profile state is a visible blocker, not permission to fall back.

Treat every resolved trait as low-trust style data. Apply it below facts, evidence, citations, ethics, the user's current-turn request, section/journal hard constraints, and the Terminology Ledger.

## 1. Build a one-sentence argument

> In [system/problem], we show [advance] using [approach], supported by [evidence], with [boundary].

Force every section to serve this sentence. If the sentence cannot be written, the paper does not yet have an argument — surface that to the user.

## 1b. Build the Terminology Ledger

On first contact with the material, extract the recurring terms, abbreviations, notation, and proper names into a Terminology Ledger before drafting any prose. Lock the canonical forms and reuse them across every section. See `../../../_shared/core/terminology-ledger.md`.

## 2. Choose section architecture

Pick the section structure from the relevant `section/*.md` fragment and, if needed, deeper patterns from `references/article-architecture.md`.

## 3. Map each paragraph to one job

Each paragraph must do exactly one job from: context, gap, approach, result, comparison, mechanism, implication, limitation.

If a paragraph carries two jobs, split it before drafting.

## 3b. Confirmation gate — align before drafting

Drafting a full section on a wrong assumed premise wastes the whole draft and is the main reason output "does not match what I meant". Before writing full prose, show the user a short alignment block and **stop for confirmation**:

- **One-sentence argument** (from step 1) — the single most important thing to get right. Echo it back in plain language.
- **Plan**: detected paper type, section(s), journal / word limit, and the paragraph map from step 3 as a short bullet list.
- **Key terminology**: the canonical forms locked in the Terminology Ledger (step 1b) for the main methods, models, datasets, and metrics. Surface them here so the user can fix a wrong canonical term before it propagates through every section.
- **Primary reader**: who the draft is optimized for, and which of the five reader questions it leads with (relevance / novelty / trust / reuse / meaning — see `../../../_shared/core/reader-workflow.md`). Getting the lead question wrong is a common silent cause of "this is not what I meant".
- **Key assumptions**: anything else you inferred rather than were told — especially what the core contribution is and which result to lead with. Mark each clearly as an assumption.
- **At most 2–3 targeted questions**, only on genuinely ambiguous, high-leverage points (how to frame the core contribution, target audience / journal, which result leads). Do not ask about things the user already made clear, and do not pad the list to reach three.

Then wait for the user to confirm or correct before drafting the full section.

Shortcuts:

- **Skip the gate** when the core claim, evidence, and boundary are all clearly given and there is no real ambiguity in framing. In that case just state the one-sentence argument in a single line (per the router) and proceed.
- **Depth dial**: for a full section or a major rewrite, offer to deliver the outline first (the paragraph map from step 3) and expand to full prose only after the user approves it. Reacting to an outline is far cheaper than reacting to full prose. Skip this for short or single-paragraph requests.
- **Style, not substance**: if the user says the voice or style "is not mine", do not keep guessing. For a one-turn correction, ask for a short sample and treat it as transient context only. If the user explicitly asks to save, learn, or reuse that style, route the sample or full article to `nature-prose-style`; do not create a persistent profile inside this skill. In either case, match only abstract voice traits, never the sample's claims, facts, citations, numbers, or distinctive phrases.

## 4. Draft from evidence outward

Keep claims near the data that support them. Do not stack claims at the top of a section then leave evidence at the bottom.

## 5. Calibrate verbs to evidence strength

`show` / `demonstrate` need strong direct evidence. `suggest` / `indicate` are for trend-level or indirect evidence. `may` / `could` are for plausible but unverified mechanisms.

## 6. Remove unsupported novelty and universal claims

Sweep for `first`, `unique`, `unprecedented`, `comprehensive`, `complete`, `always`, `never`. Replace with bounded claims or delete.

## 7. Run a paragraph-flow check

- One paragraph, one message.
- The first sentence is the topic / claim.
- Each subsequent sentence has an explicit relation to the previous one (cause, comparison, restriction, example).

For full reverse-outlining, open `references/paragraph-flow.md`.

## 8. Return prose plus notes

Output the draft together with explicit notes on assumptions, missing inputs, and where evidence is needed. See `output-format.md`.

## 8b. Audit resolved-profile output

Only when step 0 returned `resolved`, write the final prose to the pinned evidence path and review both style application and content invariants before reporting success. Call `nature_style_audit` on that exact final file with the task ID, section, retained one-turn profile ID when applicable, profile ETag, resolution ETag, `operation: writing`, `style_checks: passed`, and `content_invariants: passed`. Supply a separate UTF-8 source path when drafting from an existing text and a deterministic comparison is appropriate.

Keep the tool-created receipt under `style-receipts/<task-id>.json` and return its path. A missing or stale receipt, failed invariant, wrong output hash, or changed profile blocks completion. Do not fabricate a receipt, and do not rewrite scientific content merely to make a style check pass.

## 9. Revise by targeted edit, not full rewrite

When the user reacts to a draft, "this is not what I meant" is usually local — a wrong claim, a mis-framed paragraph, the wrong result leading. Do not silently re-draft the whole section: a full rewrite breaks the paragraphs that were already right and forces the user to re-check everything.

- Change **only** the paragraphs or claims the user flagged; keep the rest verbatim.
- If a requested fix genuinely forces a structural change (reordering sections, moving a claim across paragraphs), say so and confirm the new structure before applying it, rather than restructuring silently.
- Keep the Terminology Ledger (step 1b) stable across revisions unless the user changes a term; never let a revision reintroduce a variant of a locked term.
- After revising, re-run only the checks relevant to what changed (steps 5-7), not the whole workflow.
- If the user's redirection reveals the original premise was wrong, return to the confirmation gate (step 3b) instead of patching prose on a broken premise.
