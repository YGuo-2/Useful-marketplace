# Decision protocol (lightweight)

At genuine forks in the manuscript — where a choice materially changes the paper —
help the user decide with **structured options**, without turning every step into a
menu.

## When to offer options

Only at decision steps flagged in the genre template (typically topic selection,
outline/framing, target-journal selection). Routine execution steps (search,
read, draft, polish) do not get an options menu — just run them.

### Mandatory prose-profile ambiguity

`prose_style_choice_required` is an execution precondition, not an optional manuscript-strategy menu,
so it is the one exception to the flagged-step rule. Stop the current prose task immediately, show the
exact usable profile IDs and scopes returned by the resolver, and ask which one to use. Never rank,
merge, fuzzy-match, or infer a profile from manuscript content.

Offer the user a persistent selection through `nature_style_select` or, when they explicitly say the
choice is for this turn only, pass that exact profile ID to one resolution without changing the saved
default. If the named ID is missing or non-unique, ask again rather than guessing.

## How to offer options

- Give **2–4 options**, not a fixed count. Fewer is fine when the space is small.
- **Put the recommended option first** and give a one-sentence reason for the
  recommendation.
- Offer roughly along a risk/impact spread when it fits the choice: a safe,
  well-evidenced option; a balanced option; a higher-impact/higher-risk option.
  Do not manufacture a spread the decision does not have.
- Always allow a user-defined choice. If the user picks it, turn their input into a
  concrete plan and name any scientific/evidence/operational risk; if a risk cannot
  be resolved, mark it `需要人工核查`.

## After the choice

- Record the decision as the step's `evidence` (or a note) so it persists and a
  resumed session sees why the path was taken.
- For prose-profile selection, let `nature_style_select` persist the profile choice and inventory ETag;
  a workflow note may explain the rationale but is not selection authority.
- Do not silently auto-advance past a decision step unless the user explicitly
  asked to proceed without being consulted.

## What this is not

This is not the old four-option protocol. There is no mandatory "exactly four
options, every step" ritual and no fixed A/B/C/D labels. Keep it to real forks,
keep it short, and let the engine's `status` — not a recited menu — carry the
sense of where the user is in the flow.
