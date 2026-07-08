# Orchestration workflow

The orchestrator drives the state engine and delegates each step. Every command
below has a CLI form (run from the **repository root**) and an equivalent MCP tool.
Prefer the MCP tools when the `nature_workflow_progress` server is connected.

## 1. Seed the sequence once

If the user has no workflow yet, read the detected genre template
(`static/fragments/paper_type/<genre>.md`) and initialize **all** its steps in a
single `new` call — the template's `id: title` lines are the task list. The genre
template gives the exact task strings; do not retype them from memory.

```bash
python plugins/nature-workflow/scripts/nature_progress.py new \
  --slug review-<short-topic> --title "<paper title or topic>" \
  --task "search: 检索式生成与多源检索" \
  --task "topic: 选题与研究空白识别" \
  ...   # one --task per template row, in order
```

MCP equivalent: `nature_new_workflow` with `slug`, `title`, and `tasks` as the
array of `"id: title"` strings.

Task ids must be ASCII and ≤32 chars (engine constraint), so the template uses
English slugs for ids and Chinese for titles. Seed the whole sequence at `new`;
there is no "append a task later" command.

## 2. Drive cycle (repeat per step)

1. **Find the next step** — `status` returns `active_task`, `next_task`, and
   `task_counts`. `next_task` is the in-progress task if one is active, else the
   first pending step; a blocked step is skipped so you can park it and move on
   (§2.5), and only resurfaces once nothing else is left.
   ```bash
   python plugins/nature-workflow/scripts/nature_progress.py status --workflow <dir>
   ```
   MCP: `nature_status`.
2. **Start it** — `start <task_id>` (MCP `nature_start_task`). Only one task is
   active at a time; the engine rejects starting a second.
3. **Delegate** — from the template's delegate column, tell the user which nature-*
   skill owns this step and what inputs it needs, then let that skill run (or run
   it if the owner is the orchestrator itself). Pass the domain parameters from the
   template (e.g. "review needs top-500 strongly-relevant screening") as the task
   brief; do not re-implement the owner skill.
4. **Complete with evidence** — when a real deliverable exists, `complete <task_id>
   --evidence "<path-or-locator>"` (MCP `nature_complete_task`). The engine
   **requires** evidence; a step with no product is not complete.
5. **Or block** — if the step cannot proceed (missing input, external dependency,
   unresolved permission), `block <task_id> --reason "<why>"` (MCP
   `nature_block_task`). A blocked task lets the user park it and move on.

## 3. Progress visibility (replaces recited step numbers)

Surface where the user is by echoing the engine, not by narrating from memory:

- After each command, read back `status` / the regenerated `progress.md` and show
  the active task, what's done, and what's next.
- Derive "step N of M" from `task_counts` (completed) plus position in the ordered
  list. Do not maintain a separate hand-written progress block.

## 4. Deliverables and evidence (traceability)

- Products land under the workflow directory the engine already manages
  (`docs/nature-workflows/<workflow>/`) or a path the user chose; record that path
  as the step's `evidence`.
- Evidence is a locator (a file path, or `memory.md#M3 (L12)` style pointer), so a
  resumed session can trace every completed step to its product. This replaces the
  old `_交付结果/00-20` folder convention.

## 5. Decisions and resume

- At decision steps flagged in the template, apply `core/decision.md` before
  advancing; record the choice as evidence or a `log` note.
- To resume, `resume` / `status` reconstructs state from `nature.yml` — the active
  task, blockers, and next step are recomputed, so a new session picks up exactly
  where the last one stopped.
