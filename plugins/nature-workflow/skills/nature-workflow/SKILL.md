---
name: nature-workflow
description: Track lightweight progress for Nature skill work and route users toward the specific nature-* skill that should do the real academic task. Use when the user asks to start, resume, discover, block, complete, or log a Nature workflow, or when they ask which Nature skill to use before beginning research writing, reading, citation, figure, data, reviewer-response, paper-to-PPT, paper-to-patent, or academic-search work.
---

# Nature Workflow Router

This skill is a light wrapper around the Nature skill collection packaged in this plugin.
The individual skills remain the primary entrypoints for academic work:

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
`resume`, and `log`. Each workflow directory contains `nature.yml`, `progress.md`,
and `tasks.md`. The `nature.yml` file keeps its historical name for compatibility;
its contents are JSON.

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
