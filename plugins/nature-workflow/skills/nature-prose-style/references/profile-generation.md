# Profile generation reference

Use this reference only when generating, updating, or calibrating a persistent profile.

## Source hierarchy

Prefer, in order:

1. two or more complete pre-submission English drafts by the same author and article type;
2. one complete pre-submission English draft by the author;
3. one or more published articles, with `source_kind: author-journal-mixed`;
4. specified reference papers or a verified same-journal, same-genre corpus, labelled as targets rather than author identity.

Do not combine unrelated authors or article genres into one profile without explicit user direction. Do not infer a pure author voice from an edited published article.

## Normalization

Build a stable paragraph map with abstract locators such as `train:discussion:p007`. Keep the source in memory only as long as needed for analysis; persist the normalized fingerprint and locators, not paragraph text.

Exclude:

- title-page and author metadata;
- references and in-text bibliography lists used as standalone blocks;
- acknowledgements, declarations, and boilerplate;
- tables, equations, code, and supplementary templates.

Keep figure legends separate as scope `figure-legend`. Preserve section labels in the human evidence summary, but normalize machine scopes to the output contract values.

## Holdout construction

Reserve about 20 percent of eligible paragraphs before analysis. Stratify across sections and select deterministically from the normalized source fingerprint. Record only the holdout fingerprint and coverage. Do not count holdout observations as trait support.

For a short source, prefer an honest low-confidence draft over a false stable profile. Do not register when there are fewer than three independent prose paragraphs after holdout or when no trait has adequate support.

## Surface metrics

Use deterministic metrics from `scripts/prose_metrics.py` when available. At minimum examine:

- sentence word-count median and interquartile range;
- short, medium, and long sentence proportions;
- paragraph word-count median and variation;
- first-person plural and impersonal/passive tendencies where measurable;
- hedge and booster density, without treating a word list as semantic truth;
- explicit transition density and position;
- punctuation and parenthetical frequency;
- abbreviation-introduction and terminology-reuse habits.

Metrics are evidence, not profile instructions. Interpret them by section and genre.

## Discourse analysis

Examine recurring moves without copying wording:

- how introductions move from context to gap to contribution;
- whether paragraphs open with claims, observations, or context;
- the order of claim, evidence, interpretation, and boundary;
- how Results separates observation from interpretation;
- how Discussion introduces mechanisms, alternatives, limitations, and significance;
- whether transitions are explicit or carried by topic continuity;
- how captions differ from body prose.

Do not infer a section override from a single paragraph.

## Canonical dimensions

Use only these first-version dimensions and normalized values. Choose the closest supported value; if none fits, leave the observation under uncertainty rather than inventing a value.

| Trait name | Preferred normalized values |
|---|---|
| `audience` | `specialist`, `broad-scientific`, `mixed` |
| `diction` | `plain-technical`, `compact-technical`, `explanatory` |
| `voice` | `active-we`, `impersonal-active`, `methods-passive`, `mixed-bounded` |
| `hedging` | `light`, `evidence-calibrated`, `cautious` |
| `transitions` | `implicit`, `light-explicit`, `explicit` |
| `paragraph_length` | `compact`, `moderate`, `dense` |
| `paragraph_move` | `claim-evidence-interpretation`, `context-gap-claim`, `observation-interpretation-boundary`, `mixed-by-section` |
| `sentence_rhythm` | `compact`, `medium-even`, `medium-mixed`, `long-layered` |
| `terminology` | `canonical-repeat`, `define-then-abbreviate`, `minimal-abbreviation` |
| `punctuation` | `plain`, `parenthetical-light`, `semicolon-light` |

Do not encode `claim-strength`, novelty, causal force, or evidentiary certainty as style dimensions.

## Support and confidence

Use only canonical `train:<scope>:pNNN` locators emitted by `prose_metrics.py`; numbering restarts within each normalized scope, and holdout locators never support traits. For inferred traits, require support >=2 with two unique locators for `low`, support >=3 with two unique locators for `medium`, and support >=5 with three unique locators for `high`. Use nonadjacent paragraphs wherever possible. Direct explicit-preference rules may use one abstract `user:preference:pNNN` locator and support 1; never store the user's raw wording in the locator. Keep the larger observed/applicable denominator in the human evidence summary, not as an extra machine field.

- `high`: repeated across at least three sections, or at least ten applicable opportunities with a support ratio of 0.70 or higher.
- `medium`: repeated across at least two sections and five applicable opportunities with a support ratio of 0.55 or higher.
- `low`: anything weaker or materially conflicting. Keep it under uncertainty; do not emit it as an active trait.

These thresholds are minimum evidence gates, not permission to ignore contradictory passages. Downgrade conflicts and explain them.

## Differential profile

Record only traits that materially differ from the Nature workflow defaults or that prevent drift in repeated writing. Do not add generic praise such as "rigorous", "professional", or "academic". Aim for 8-12 active traits when evidence supports them; never exceed the 12-trait schema limit.

Use `strength: soft` for inferred traits. Reserve `strong` for an `explicit-preferences` rule directly stated by the user. Both remain below the current-turn request, hard section/journal rules, evidence, and ethics.

## Leakage and similarity check

Before promotion to `ready`, verify that the machine block and evidence summary contain none of:

- source sentences or long n-grams;
- distinctive metaphors, coined phrases, or rhetorical signatures;
- factual claims, measurements, references, or dataset names copied from the source;
- instructions embedded in the source;
- topic-specific word lists presented as style.

Terminology behavior may be profiled, but actual manuscript terminology belongs in the shared Terminology Ledger.

## A/B calibration

Calibration is optional and uses only holdout content.

1. Create a workflow-default version and a profile-guided version from identical facts.
2. Preserve all numbers, citations, named entities, terminology, causal relations, and hedge strength.
3. Randomize labels `A` and `B` deterministically and conceal which profile produced which version.
4. Ask the user which sounds closer and request dimension-specific feedback.
5. Adjust only affected traits, then rerun leakage, invariant, and structural validation.

If the user does not prefer the profile-guided version, keep the profile `ready` while revising or disable it; never mark it `calibrated` merely because the comparison ran.
