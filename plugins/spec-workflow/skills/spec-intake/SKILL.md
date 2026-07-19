---
name: spec-intake
description: Explicit activation only. Internal step of a user-invoked spec-workflow. Select only after the active spec-workflow router hands off, or when the user explicitly names spec-intake and thereby opts into the plugin; otherwise do not select.
---

# Spec workflow Intake

Use this as the first step in the Spec workflow plugin after `<specs_dir>` is selected. Its job is to turn a vague request into a route-ready, spec-ready handoff. It does not generate source code and does not create a standalone `<specs_dir>/intake.md`; the handoff must be carried into the selected branch's primary spec artifact.

## Activation Boundary

This skill may run only inside a user-initiated spec-workflow run. If the user explicitly names `spec-intake` directly, treat that as plugin opt-in but enter through the `spec-workflow` router and directory-selection gate first. Generic clarification requests must not activate it.

## Required Announcement

If the entry router has not already printed the announcement, print:

```markdown
我读到了Spec-intake技能。
```

## Hard Rules

- Clarify before routing and route before generating spec artifacts.
- Inspect discoverable project context before asking user-facing questions.
- Do not ask for facts that can be found in the repo, docs, configs, schemas, tests, logs, issue text, or existing specs.
- Ask the highest-leverage unresolved question, normally one question per round. Use 2-3 tightly related options only when a structured choice materially reduces ambiguity.
- Do not leave intake just because one question was answered. Leave only when the Intake Completion Gate is `complete` or `assumptions-accepted`.
- Non-goals and decision boundaries are mandatory gates for non-trivial work.
- If the user says to proceed with assumptions, record the accepted unknowns as assumptions or risks in the downstream spec.
- Do not create `<specs_dir>/intake.md`; write the handoff into `product.md`, `requirements.md`, or `bugfix.md`.
- Do not write business source code before the selected branch's approval phrase is received and frozen through `spec_progress.py approve`.

## State A: Preflight Context Scan

Before asking, inspect likely sources of truth when available:

- Existing specs under the selected `<specs_dir>` and the `docs/specs/` workflow directory catalogue
- Project rules such as `constitution.md`, `CONVENTIONS.md`, `README.md`, ADRs, architecture docs, migration notes, and glossary/context files
- Stack manifests such as `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, Gradle/Maven files, or similar
- Relevant code paths, tests, logs, screenshots, issue text, alerts, or recent changes named by the user

Classify collected facts:

- `[from-code][auto-confirmed]`: exact repo facts with no decision attached
- `[from-code]`: repo patterns or inferred facts that need user confirmation before becoming requirements
- `[from-user]`: goals, preferences, scope, non-goals, tradeoffs, acceptance criteria, and business rules
- `[assumption]`: unknowns the user explicitly allows the workflow to carry forward

Summarize what is already clear before asking.

## State B: Multi-Round Gap Check

Progress through the stages in order. Stay on a stage until the answer is concrete enough to use in a spec, then move forward.

1. Intent and outcome:
   - goal, user value, expected end state, and why this change matters now
2. Scope and boundaries:
   - in-scope areas, out-of-scope areas, affected modules, public contracts, integrations, migration, compatibility, and rollback expectations
3. Non-goals and decision boundaries:
   - what must not be changed, what the agent may decide autonomously, and what needs human confirmation
4. Success criteria:
   - acceptance criteria, definition of done, verification evidence, and release/operational expectations
5. Route-specific evidence:
   - Requirements-First: user stories, EARS/GWT scenarios, non-functional requirements, safety/security/data/performance constraints
   - Design-First: HLD/LLD granularity, fixed design constraints, locked decisions, open decisions, interfaces, data flow, state transitions, alternatives
   - Bugfix: current incorrect behavior, expected behavior, unchanged behavior, reproduction, frequency, environment/version, recent changes, root-cause confidence
6. Risk pressure pass:
   - permissions, authorization, privacy, sensitive data, concurrency, data consistency, cache consistency, migrations, incidents, hotfixes, monitoring, and rollback

For each user answer, pressure-test at least one of:

- ask for a concrete example, counterexample, or evidence signal
- expose a hidden assumption or dependency
- force a tradeoff or boundary
- compare a fuzzy term against repo terminology or code behavior
- stress-test the boundary with one concrete scenario

## State C: Ask Or Continue

If a material gate remains unresolved, stop and ask only the next highest-value question:

```markdown
## 需求澄清问题

Round [n] | Target: [goal / scope / non-goals / decision-boundaries / success-criteria / route-specific-risk]

[一个会改变规范、路由、范围、风险或验收标准的问题]
```

If the user answers but another material gate is still open, ask the next round. Do not generate specs yet.

## Intake Completion Gate

Intake may hand off only when every item below is either confirmed or explicitly accepted as an assumption:

- Goal and user-visible outcome
- Success criteria and verification evidence
- Scope and affected surfaces
- Non-goals
- Decision boundaries
- Constraints: compatibility, migration, rollback, security/privacy, performance, concurrency/data consistency where relevant
- Route: Requirements-First, Design-First, or Bugfix
- Assumptions and risks that must enter the downstream spec

Allowed handoff statuses:

- `complete`: all gates are concrete enough for spec generation
- `assumptions-accepted`: unresolved gates exist, but the user explicitly accepted them as assumptions/risks
- `blocked`: a material gate is unresolved and cannot safely be assumed

## State D: Intake Handoff

When the gate is `complete` or `assumptions-accepted`, output this exact shape and continue to the router:

```markdown
## Intake Handoff / 澄清交接摘要

- Status: complete | assumptions-accepted
- Route recommendation: Requirements-First | Design-First | Bugfix
- Confirmed facts:
  - [from-code/from-user facts that must enter the spec]
- Scope:
  - [in-scope surfaces]
- Non-goals:
  - [explicit exclusions]
- Decision boundaries:
  - [agent-owned vs human-owned decisions]
- Success criteria:
  - [acceptance and verification signals]
- Assumptions:
  - [accepted assumptions, or n/a]
- Risks:
  - [risks to carry into Analyze Requirements / design / tasks, or n/a]
- Next step: return to `spec-workflow` routing.
```

If the status is `blocked`, ask for the missing decision and stop.
