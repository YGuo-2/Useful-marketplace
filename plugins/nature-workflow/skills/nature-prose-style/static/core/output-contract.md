# Prose-profile output contract

All persistent artifacts live under the explicitly selected workflow directory:

```text
docs/nature-workflows/<paper>/
|-- nature.yml
|-- prose-profiles/
|   `-- <profile-id>.md
|-- style-calibration/
|   `-- <profile-id>.md
`-- style-receipts/
    `-- <task-id>.json
```

`style-calibration/` is optional. Receipts are written by `nature_style_audit`, not by the profile-generation agent. Do not hand-edit the `prose_style` inventory in `nature.yml`.

## Profile document

Use Markdown beginning with the fixed `# Prose Profile` heading and containing exactly one fenced `json` block. The validator and resolver consume only that JSON object. Put any further human-readable explanation after the fence under the documented headings as short abstract bullets; it is non-executable. Do not add a second JSON fence or profile sentinels.

````markdown
# Prose Profile

```json
{
  "schema_version": 1,
  "id": "author-main",
  "status": "draft",
  "source_kind": "author-draft",
  "source_fingerprint": "sha256:<64-lowercase-hex-characters>",
  "language": "en",
  "scopes": ["global", "abstract", "intro", "methods", "results", "discussion", "conclusion"],
  "traits": [
    {
      "name": "voice",
      "value": "active-we",
      "scope": ["intro", "results", "discussion"],
      "confidence": "high",
      "support": 14,
      "source_refs": ["train:intro:p004", "train:results:p011", "train:discussion:p007"],
      "strength": "soft"
    }
  ],
  "exclusions": ["source facts", "source citations", "distinctive phrases", "claim strength"],
  "created_at": "<RFC3339-UTC>",
  "updated_at": "<RFC3339-UTC>"
}
```

# Evidence summary

- Summarize support counts and covered sections without quoting source prose.

# Uncertainty and conflicts

- List observations that were not promoted into active traits.
````

Replace every placeholder before validation. Preserve `created_at` on update and set `updated_at` from the current system clock.

## Exact machine schema

The top-level object may contain only:

`schema_version`, `id`, `status`, `source_kind`, `source_fingerprint`, `language`, `scopes`, `traits`, `exclusions`, `created_at`, `updated_at`.

- Require `schema_version: 1`.
- Require the filename `prose-profiles/<id>.md`; `id` must match `[a-z][a-z0-9-]{0,63}` and the filename stem.
- Allow status `draft`, `ready`, `calibrated`, or `invalid`; only `ready` and `calibrated` may be registered.
- Allow `source_kind` `author-draft`, `author-journal-mixed`, `explicit-preferences`, `journal-corpus`, or `reference-paper`.
- Require `source_fingerprint` in the form `sha256:` plus 64 lowercase hexadecimal characters.
- Require `language: en` in schema version 1.
- Allow scopes only from `global`, `title`, `abstract`, `intro`, `related-work`, `method`, `methods`, `results`, `experiments`, `discussion`, `conclusion`, and `figure-legend`.
- Require 1-12 traits. Each trait may contain only `name`, `value`, `scope`, `confidence`, `support`, `source_refs`, and `strength`.
- Allow trait names `audience`, `diction`, `hedging`, `paragraph_length`, `paragraph_move`, `punctuation`, `sentence_rhythm`, `terminology`, `transitions`, and `voice`.
- Require a non-empty allowed scope list, confidence `low|medium|high`, positive integer support, abstract source locators, and strength `soft|strong`. A trait scope must stay within the profile's top-level scopes unless the top-level list contains `global`. For inferred traits, `low` requires support >=2 and two unique locators, `medium` requires support >=3 and two unique locators, and `high` requires support >=5 and three unique locators. An explicit-preferences rule requires support >=1 and one locator. `low` confidence may remain in a draft but cannot enter a ready/calibrated profile.
- Use only canonical training locators emitted by `prose_metrics.py`: `train:<scope>:pNNN` (up to six digits). Paragraph numbering restarts within each normalized scope. Holdout locators use `holdout:<scope>:pNNN` and must never appear in trait `source_refs`. Direct preferences use abstract `user:preference:pNNN` locators, never the user's raw wording.
- Use `strong` only for a direct `explicit-preferences` rule stated by the user. Inferred article traits remain `soft`; neither value can override higher-priority invariants.
- Do not emit duplicate keys. Reject duplicate or unknown fields, path-like IDs, unsupported enums, raw source passages, and invalid fingerprints.
- Allow exclusions only from `source facts`, `source numbers`, `source citations`, `distinctive phrases`, `claim strength`, `canonical terminology`, and `causal direction`.

Trait `value` must use the normalized vocabulary in `references/profile-generation.md`; the validator rejects nonstandard values so source prose and embedded instructions cannot enter the resolver.

## Calibration record

When calibration is run, record outside the profile JSON:

- profile ID and pre/post profile ETags;
- holdout fingerprint and section coverage;
- randomized variant labels;
- the user's selection and dimension-specific feedback;
- trait additions, removals, or strength changes;
- invariant-check result.

Do not include the complete holdout text. Short generated comparison snippets may be retained only when the user explicitly asks to save them and they contain no sensitive material.

## User-facing result

Report:

1. the absolute profile path;
2. source kind;
3. status (`draft`, `ready`, `calibrated`, or `invalid`);
4. stable traits and important uncertainty;
5. selection state (`auto_single`, `needs_choice`, or `user_selected`);
6. the downstream effect.

For one usable profile, state plainly that it was selected automatically and will be resolved by future writing/polishing tasks. For multiple usable profiles, list their IDs and ask before any prose task. Do not claim successful application until an audit receipt exists for the actual output.
