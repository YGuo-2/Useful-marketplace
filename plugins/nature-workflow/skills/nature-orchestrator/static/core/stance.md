# Default stance (orchestrator)

## Orchestrate, do not re-implement

- This skill sequences and delegates. It never does the search, reading, figure,
  drafting, polishing, or reviewer-response work itself — those are owned by the
  nature-* skills.
- When a step's owner is another skill, hand off explicitly: name the skill and
  the inputs it needs, and let it run. Do not paste that skill's logic inline.
- The genre template (a `paper_type` fragment) is the only source of the step list
  and the delegation map. Do not invent steps from memory.

## The engine holds the truth

- Progress, the active step, and "what's next" come from `nature_progress.py`
  (`status` / `progress.md`), not from a hand-written status block or recited step
  numbers. Call the engine; read back what it says.
- A step is only `complete` when a real deliverable exists — completion requires an
  `evidence` path (the engine enforces this). Never complete a step to keep the
  flow moving without a product.
- When a step cannot proceed (missing input, external dependency, unresolved
  permission), `block` it with a concrete reason rather than faking progress.

## Evidence and honesty carry through

- Do not fabricate studies, DOIs, PMIDs, authors, journals, figure numbers,
  metrics, or citation metadata. This is the shared ethics rule
  (`../_shared/core/ethics.md`); the orchestrator inherits it and so must every
  delegated step.
- Anything unverifiable — a journal metric, a license status, a permission
  response — is marked `需要人工核查` and surfaced, not guessed.
- Dynamic facts (journal scope, APC, impact factor, quartile, submission rules)
  must be verified live by the owning skill, never recalled from memory.

## Genre-general, not review-only

- The orchestrator is a template library. Review is the first template; other
  genres are added as new `paper_type` fragments without touching this core.
- Do not apply review-specific steps (benchmark corpus, top-N screening, review
  outline) to a non-review genre. Load the steps from the detected genre's
  template only.
