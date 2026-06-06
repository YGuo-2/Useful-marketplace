---
name: spec-design-first
description: Use for Spce workflow Feature / Design-First work when the user explicitly starts from technical design, architecture constraints, ADRs, high-level design, low-level design, or a fixed implementation approach. Generates design.md, requirements.md, and tasks.md before implementation.
---

# Spce workflow Design-First

Use this branch when the technical design is the starting point and requirements must be derived from that design.

If the entry router has not already printed the announcement, print:

```markdown
我读到了Spce workflow技能。
我会按照“Feature / Design-First”分支来完成。
```

## Hard Rules

- Do not write business source code until the human explicitly replies the preferred approval phrase `批准规范，启动执行`.
- For compatibility, also accept the legacy Design-First approval phrase `批准 design-first 规范，启动执行`.
- Generate or update spec artifacts in `docs/specs/`; they are the source of truth.
- New specs must also generate `docs/specs/spec.yml` and `docs/specs/progress.md` from the templates in `../../assets/templates/`.
- `design.md` is the primary truth source for this branch.
- `requirements.md` must be derived from `design.md`; do not add unsupported product scope. It must include Kiro-style Analyze Requirements conclusions before finalizing tasks.
- If the request is a pure product goal with no technical design intent, reroute to `../spec-requirements-first/SKILL.md`. If the user explicitly asks for Design-First but provides incomplete design input, stay in State A and clarify the design starting point.

## High-Risk Warning

If the task involves authentication, authorization, payments, billing, database schema changes, data repair, distributed consistency, cache consistency, secrets, encryption, sensitive data, incident mitigation, rollback, or hotfix work, include this warning even when the router was skipped:

```markdown
> [!WARNING]
> 高风险变更警告：当前任务涉及核心系统或高影响范围区域，必须进行人类深度审查，切勿草率合并。
```

## Intake Precondition

Before choosing design granularity or entering State A, if the current conversation does not already include a `spec-intake` summary or a clear no-material-questions decision, read and follow `../spec-intake/SKILL.md`. If intake asks questions, stop and wait for the human answer before generating specs.

## Design Granularity

Choose one before generating artifacts:

- `High Level Design`: system boundaries, component topology, service split, deployment, dependencies, and key interfaces
- `Low Level Design`: module/class responsibilities, function signatures, state transitions, algorithms, detailed data structures, and local implementation flow

If both are needed, start with High Level Design and expand to Low Level Design only where the implementation needs it.

## State A: Design Clarification

Inspect project context before asking questions: existing specs, architecture docs, ADRs, manifests, interface drafts, migration notes, and related code paths.

Clarify only design-critical gaps:

- design objective and fixed constraints
- selected granularity
- affected system boundary, components, APIs, data flow, and state changes
- performance, security, compliance, compatibility, and migration constraints
- decisions already locked vs. decisions still open
- alternatives considered and rejection reasons when available

If clarification is needed, output a concise numbered question list. Unknowns may be recorded as assumptions or risks if the user accepts that.

## State B: Spec Artifact Generation

Use the plugin templates from `../../assets/templates/`:

- `design_first_design_template.md`
- `requirements_template.md`
- `design_first_tasks_template.md`
- `progress_template.md`
- `spec_index_template.yml`

Generate:

- `docs/specs/design.md`: design granularity, system or module boundaries, relationships, key interfaces, data flow, constraints, rejected alternatives, and risks
- `docs/specs/requirements.md`: requirements and acceptance criteria derived from `design.md`, with clear markers for assumptions
- `docs/specs/tasks.md`: ordered atomic tasks that follow design dependencies, using `- [ ]`, with structured fields: status, files, verify, evidence, depends_on, risk, covers, and parallelizable
- `docs/specs/progress.md`: resume entrypoint with workflow status, current task, approval state, branch, commit, blockers, and recovery notes
- `docs/specs/spec.yml`: Kiro-compatible machine index with workflow, mode, approval, risk level, artifact paths, requirement IDs, task graph, current task, and checkpoint

Default mode is `strict`. Use `quick` only when the user explicitly authorizes Quick Plan and the risk level is low; record the Quick Plan reason in `requirements.md` and `spec.yml`.

If the selected granularity is `Low Level Design`, `design.md` must also include module/class responsibilities, function signatures and contracts, algorithm flow, state transitions, and detailed data structures.

Before review, replace all template placeholders with concrete content. If a template section does not apply, state that explicitly with the reason instead of leaving placeholder text.

If `requirements.md` exposes a gap in `design.md`, update `design.md` first, then derive requirements and tasks again.

The preferred approval phrase for implementation is:

```text
批准规范，启动执行
```

The legacy Design-First phrase remains valid for compatibility:

```text
批准 design-first 规范，启动执行
```

Suggested validation:

```bash
python <plugin-root>/scripts/validate_spec.py docs/specs/ --workflow design-first
python <plugin-root>/scripts/spec_progress.py init docs/specs/
python <plugin-root>/scripts/validate_spec.py docs/specs/ --resume
```

This is a structural integrity check only. Passing validation does not approve implementation; implementation still requires an accepted approval phrase.

## State C: Controlled Implementation

Only enter this state after explicit approval.

When the approval phrase is received, update any generated status or approval-record fields in the spec artifacts before implementation.

Implementation rules:

- Read `docs/specs/design.md`, `docs/specs/requirements.md`, and `docs/specs/tasks.md`.
- Select only the first unchecked task in `tasks.md`.
- Before editing business code for that task, call `spec_start_task` through MCP or run `python <plugin-root>/scripts/spec_progress.py start docs/specs/ T-xxx`.
- Implement only behavior inside the approved design boundary.
- Add or update tests that prove both design constraints and derived requirements.
- If implementation conflicts with `design.md` or any approved spec artifact must change, stop code work, return to State B, update the specs, run sync-check, set approval to `reapproval-required`, and wait for an accepted approval phrase again before continuing.
- Run verification and perform at most three self-healing loops.
- After passing verification, call `spec_complete_task` through MCP or run `python <plugin-root>/scripts/spec_progress.py complete docs/specs/ T-xxx --evidence "<verification evidence>"`. Do not manually mark `- [x]` without recorded evidence.
- If blocked, call `spec_block_task` or `python <plugin-root>/scripts/spec_progress.py block docs/specs/ T-xxx --reason "<reason>"`.
- If skipped, call `spec_skip_task` or `python <plugin-root>/scripts/spec_progress.py skip docs/specs/ T-xxx --approval "<human approval evidence>"`.
- Provide a commit message suggestion in this form:

```text
feat(scope): short description

Implements task: [task description]
Spec: docs/specs/tasks.md
```

If unchecked tasks remain, ask whether to continue only after the current task is complete.

If no unchecked tasks remain in `docs/specs/tasks.md`, read and follow `../spec-acceptance/SKILL.md` before reporting the whole workflow complete.
