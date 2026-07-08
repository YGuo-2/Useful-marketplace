---
name: nature-workflow
description: Track lightweight progress for Nature skill work and route users toward the specific nature-* skill that should do the real academic task. Use when the user asks to start, resume, discover, block, complete, or log a Nature workflow, or when they ask which Nature skill to use before beginning research writing, reading, citation, figure, data, reviewer-response, paper-to-PPT, paper-to-patent, or academic-search work.
---

# Nature Workflow Router

This skill is a light wrapper around the Nature skill collection packaged in this plugin.

For an **end-to-end manuscript** (topic → submission), use `nature-orchestrator`: it
drives the whole lifecycle as a task sequence in the state engine and delegates each
step to the skill that owns it. For a **single isolated task**, the individual skills
remain the primary entrypoints for academic work:

- `nature-reader` for full paper reading, translation, and source-anchored Markdown readers.
- `nature-paper2ppt` for paper-to-PPTX journal club or group meeting decks.
- `nature-polishing` and `nature-writing` for academic prose polishing, translation, and drafting.
- `nature-citation` and `nature-academic-search` for citation support, literature search, verification, and reference files.
- `nature-figure` for publication-grade scientific figures.
- `nature-data` for data availability, repository, and FAIR metadata work.
- `nature-response` and `nature-reviewer` for reviewer responses and mock peer review.
- `nature-paper-to-patent` for evidence-grounded Chinese invention patent drafts.

Use the workflow state tools only to create or maintain local progress records under
`docs/nature-workflows/` by default. They do not approve specs, enforce code guards,
run acceptance rounds, or replace the domain-specific skills.

## Progress Tools

The plugin provides both CLI and MCP access to the same state engine. Run all
CLI commands below from the repository root (repo root); the paths are relative
to it:

- CLI: `python plugins/nature-workflow/scripts/nature_progress.py <command>`
- MCP server: `plugins/nature-workflow/mcp/nature_progress_server.py`

Supported actions are `new`, `discover`, `status`, `start`, `complete`, `block`,
`resume`, `log`, `add-task`, `remove-task`, `genre`, and `spec`. The orchestrator
seeds the task sequence from a genre template at `new`; `add-task`/`remove-task`
adjust it mid-flow (e.g. injecting a reviewer pre-check) and `genre` persists the
detected paper type. Each workflow directory contains `nature.yml`,
`progress.md`, and `tasks.md`, plus an optional `spec.md` format contract (see
the Spec gate below). The `nature.yml` file keeps its historical name for
compatibility; its contents are JSON.

## Spec Gate (optional format contract)

A workflow may keep a `spec.md` beside `nature.yml`: a **format-only** contract —
the per-element typographic style sheet (font, size, weight, alignment, indent,
line spacing, space before/after, numbering) that output skills follow so a
manuscript's formatting stays consistent. It is journal-agnostic: the same table
holds different values per target venue. It is **not** content, word budgets, or
submission rules, and it is a **soft** contract — editable anytime, never frozen.

**Trigger — lazy, user's choice.** Do not force this at `new`. The first time a
producing skill runs (`nature-writing`, `nature-polishing`, `nature-figure`) and
the workflow's spec status is `unset`, ask the user whether to build a format
spec. Reader/search/citation work needs no spec, so never gate on it there.

- User declines → record `spec --status skipped` so no skill re-prompts; skills
  use their own defaults (current behavior).
- User accepts → author `spec.md`, then record `spec --status ready
  --source <template|dictation> [--path spec.md]`. Downstream producing skills
  read `spec.md` as the format contract.

See `plugins/nature-workflow/assets/templates/spec_nature_example.md` for a worked
example of the style-sheet table (Nature Article) — author `spec.md` in that same
shape, swapping values for the target venue.

Two branches to author `spec.md`:

- **① Template file provided.** The user supplies a format source (journal
  guideline, thesis format rules, a laid-out sample `.docx`/`.tex`/`.pdf`, or a
  submission guide). Parse it, extract each element's typographic properties into
  the style-sheet table. Where the template is silent, **ask the user
  element-by-element — do not invent values**; mark anything still unknown as
  `未指定 · 按模板默认`.
- **② No template → dictation.** The user describes the format verbally. Map each
  stated rule into the matching style-sheet row. For elements the user did not
  mention, prefill sensible defaults and **flag which rows are defaults** for the
  user to confirm; do not silently decide for them.

Record the decision through the state engine so it persists and stops re-prompts:

```bash
python plugins/nature-workflow/scripts/nature_progress.py spec --status ready --source dictation --workflow <workflow-dir>
python plugins/nature-workflow/scripts/nature_progress.py spec --status skipped --workflow <workflow-dir>
```

The MCP tool `nature_spec` mirrors the same operation. `status` is `unset` by
default on a new workflow, `skipped` after the user declines, `ready` once a
`spec.md` exists.

## Project Memory

Each paper-level workflow may also keep a persistent `memory.md` beside
`nature.yml`, `progress.md`, and `tasks.md`. Treat this as project memory for one
paper: read it when resuming work in that workflow, and write concise durable
facts that future agents should remember. Do not use progress files as memory;
the only intended contact point is that `complete` and `block` moments should
prompt the agent to consider whether a memory entry needs to be updated.

Memory entries must use exactly this format:

```markdown
## M3 · 引用风格
<!-- updated: 2026-06-20T12:00:00Z -->
RIS 导出, EndNote 兼容。
```

Rules are enforced by `nature_memory.py check`: title format is
`## M<integer> · <title>`, IDs must be unique, title length is at most 40
characters, body length is at most 280 characters and at most 4 lines, and the
whole file may contain at most 12 entries.

The agent writes the title and body, but must not handwrite timestamps. After
editing an entry, run `python plugins/nature-workflow/scripts/nature_memory.py
touch <entry-id> --root docs/nature-workflows --workflow <workflow-dir>` so the
script stamps `<!-- updated: <ISO8601 UTC> -->` from the system clock. Then run
`check`, and finally run `index` to synchronize the project-root `AGENTS.md`
sentinel index. The index command only rewrites the sentinel section.

CLI examples (run from the repository root):

```bash
python plugins/nature-workflow/scripts/nature_memory.py touch M3 --workflow <workflow-dir>
python plugins/nature-workflow/scripts/nature_memory.py check --workflow <workflow-dir>
python plugins/nature-workflow/scripts/nature_memory.py index --root docs/nature-workflows
```

MCP tools mirror the same operations: `nature_memory_touch`,
`nature_memory_check`, `nature_memory_index`, and `nature_memory_list`.

When a final answer relies on a memory entry, cite only its position, for
example `memory.md#M3 (L12)`. Do not copy the memory body into the final answer
unless the user explicitly asks.
