# Spec Coding Marketplace

This repository provides the Codex plugin marketplace entry for `spec-coding`.

## Import in Codex

Use the Codex "Add plugin marketplace" dialog:

- Source: `YGuo-2/spec-coding-marketplace`
- Git ref: `main`
- Sparse path: leave empty

Codex expects the marketplace manifest at `.agents/plugins/marketplace.json`.
The plugin source is at `plugins/spec-coding`.

## What It Does

`spec-coding` is a spec-first workflow for changes where correctness, scope control, and reviewability matter more than speed.

It includes six skills:

- `spec-intake`: inspect context first, then ask only material clarification questions.
- `spec-coding`: route the request to the right workflow branch.
- `spec-requirements-first`: create product-led feature specs.
- `spec-design-first`: create design-led specs from fixed architecture or technical constraints.
- `spec-bugfix`: create evidence-led bugfix specs before code changes.
- `spec-acceptance`: run final multi-agent acceptance after all approved tasks are complete.

Use it for complex features, cross-module refactors, design-first work, regressions, production fixes, or high-risk changes. For tiny local edits, the workflow can be heavier than the task.

## Workflow

All generated artifacts live in `docs/specs/`; chat-only plans are not the source of truth.

1. Intake clarifies goal, scope, risk, and acceptance criteria.
2. Router selects one branch:
   - Requirements-First: product goal or new capability without fixed technical design.
   - Design-First: architecture, ADR, HLD/LLD, or fixed technical approach drives the work.
   - Bugfix: restore existing expected behavior with evidence and regression protection.
3. The selected branch writes spec artifacts and asks for approval.
4. Implementation proceeds one unchecked `tasks.md` item at a time.
5. When no unchecked tasks remain, `spec-acceptance` performs final review and adversarial review with sub-agents.

The preferred implementation approval phrase for every branch is:

```text
批准规范，启动执行
```

Legacy phrases remain valid for compatibility:

```text
批准 design-first 规范，启动执行
批准 bugfix 规范，启动执行
```

Passing validation is not approval. The human approval phrase is still required before writing business source code.

## Validation

Run the structural validator against the generated specs:

```bash
python plugins/spec-coding/scripts/validate_spec.py docs/specs/ --workflow requirements-first
python plugins/spec-coding/scripts/validate_spec.py docs/specs/ --workflow design-first
python plugins/spec-coding/scripts/validate_spec.py docs/specs/ --workflow bugfix
```

`--workflow auto` is the default when the directory contains exactly one recognizable artifact set.

The validator checks required files, unresolved template placeholders, formal GWT lines, branch-specific task IDs, LLD depth rules, and basic structural sections. It does not prove semantic quality, root-cause correctness, minimal scope, test strength, or safe rollout.

Color output defaults to `auto` and can be controlled with:

```bash
python plugins/spec-coding/scripts/validate_spec.py docs/specs/ --color never
```

## Final Acceptance

Final acceptance is intentionally strict. It requires explicit authorization to orchestrate sub-agents for first-wave review and adversarial review. If the current environment cannot run sub-agents, the workflow is blocked at acceptance; it must not be downgraded to a single-agent self-review or reported as complete.

Confirmed acceptance issues route back into the Bugfix branch, then acceptance is repeated after the fix.

## High-Risk Work

Authentication, authorization, payments, billing, database schema changes, data repair, distributed consistency, cache consistency, secrets, encryption, sensitive data, incidents, rollback, and hotfix work require a visible warning and human deep review before merge.

## Development Checks

Useful local checks for this repository:

```bash
python -m py_compile plugins/spec-coding/scripts/validate_spec.py
python plugins/spec-coding/scripts/validate_spec.py --help
python plugins/spec-coding/scripts/test_validate_spec.py
python -m json.tool plugins/spec-coding/.codex-plugin/plugin.json
git diff --check
```
