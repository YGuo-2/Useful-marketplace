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

The plugin provides both CLI and MCP access to the same state engine:

- CLI: `python plugins/nature-workflow/scripts/nature_progress.py <command>`
- MCP server: `plugins/nature-workflow/mcp/nature_progress_server.py`

Supported actions are `new`, `discover`, `status`, `start`, `complete`, `block`,
`resume`, and `log`. Each workflow directory contains `nature.yml`, `progress.md`,
and `tasks.md`. The `nature.yml` file keeps its historical name for compatibility;
its contents are JSON.
