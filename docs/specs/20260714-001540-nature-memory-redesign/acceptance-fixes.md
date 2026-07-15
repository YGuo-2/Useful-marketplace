# Acceptance Fixes

> **Source:** E:/CodeProject/Useful-marketplace/docs/specs/20260714-001540-nature-memory-redesign/acceptance_state.json
> **Round:** 1
> **Policy:** rounds 1-3 fix all actionable issues; round 4+ auto-fix P0-P2 only
> **Original tasks:** 12 frozen tasks; do not append acceptance fixes to tasks.md

## Fix Queue

| Fix ID | Issue IDs | Severity | Units | Status | Evidence |
|:---|:---|:---|:---|:---|:---|
| F-001 | I-001 | P1 | U-001 | done | nature_memory.py stable/legacy/title resolver plus test_nature_memory.py stable touch regression; 105-test suite passed. |
| F-002 | I-002 | P2 | U-001 | done | nature_memory.py legacy show returns legacy_ref without fabricated locator; legacy show regression passed. |
| F-003 | I-003 | P1 | U-002 | done | resolve_memory_path is used by check/list/index/touch and rejects symlink memory paths; safety suite passed with Windows symlink skip recorded. |
| F-004 | I-004 | P1 | U-002 | done | mutation local Git proof runs inside workflow_memory_lock; local fail-closed and concurrency tests passed. |
| F-005 | I-005 | P2 | U-002 | done | versioned KNOWN_SECRET_RE uses token boundaries; secret safety tests passed. |
| F-006 | I-006 | P2 | U-002 | done | local diagnostics include memory_path, scope, retryable and repair guidance; local safety tests passed. |
| F-007 | I-007 | P1 | U-003 | done | workflow lock initialization converts Windows initialization failures to retryable lock_unavailable; concurrency suite passed. |
| F-008 | I-008 | P1 | U-003 | done | atomic replace performs locked snapshot and expected_etag recheck; external file-change regression passed. |
| F-009 | I-009 | P2 | U-003 | done | etag_conflict and file_changed_outside_lock include current and expected entry/file ETags; concurrency tests passed. |
| F-010 | I-010 | P2 | U-003 | done | separate-process CAS regression plus thread concurrency tests passed; Unix branch remains covered by platform implementation. |
| F-011 | I-011 | P1 | U-004 | done | same-file supersedes existence, boundary and cycle validation added; cross-boundary regression passed. |
| F-012 | I-012 | P2 | U-004 | done | show returns scope, workflow_dir, memory_path, locator, legacy_ref and successor locators; MCP lifecycle smoke passed. |
| F-013 | I-013 | P2 | U-004 | done | real JSON-RPC show/forget and lifecycle calls are covered by test_nature_progress_server.py; 26 progress/MCP tests passed. |
| F-014 | I-014 | P2 | U-005 | done | consolidate plan/apply require at least two active sources; consolidation tests passed. |
| F-015 | I-015 | P2 | U-005 | done | hard_file_budget returns manual-backup/Git-reviewed recovery guidance; hard-budget regression passed. |
| F-016 | I-016 | P1 | U-006 | done | touch resolves stable ID, alias and unique title and fails closed on ambiguity; compatibility tests passed. |
| F-017 | I-017 | P2 | U-006 | done | legacy list preserves id=null, legacy_aliases and legacy_ref with append-only fields; list tests passed. |
| F-018 | I-018 | P2 | U-006 | done | legacy shims return structured deprecated fields; check/index/list/show/touch compatibility paths covered. |
| F-019 | I-019 | P2 | U-006 | done | malformed sentinel errors include exact marker positions and preserve backup; sentinel safety tests passed. |
| F-020 | I-020 | P2 | U-006 | done | pre-commit-nature-memory executed through Git Bash and returned hook_exit=0. |
| F-021 | I-021 | P1 | U-007 | done | recall uses a minimum valid response budget and compact bounded fallback; recall tests and deterministic eval passed. |
| F-022 | I-022 | P2 | U-007 | done | exact ID/title/phrase scoring tiers now dominate token-heavy matches; recall ranking tests passed. |
| F-023 | I-023 | P2 | U-007 | done | MCP recall exposes all_workflows and explicit cross-workflow read dispatch; real JSON-RPC all_workflows smoke passed. |
| F-024 | I-024 | P1 | U-008 | done | migration failures are structured and CLI migrate returns exit code 2; missing-workflow probe passed. |
| F-025 | I-025 | P2 | U-008 | done | migration --all preserves per-workflow results and reports partial operation; migration suite passed. |
| F-026 | I-026 | P2 | U-008 | done | migration --all supports shared and local scope with explicit local protection; local migration test passed. |
| F-027 | I-027 | P2 | U-008 | done | migration errors include project_root, workflow_dir, scope, memory_path and current ETag context where available. |
| F-028 | I-028 | P2 | U-008 | done | migration CLI/API paths and JSON-RPC lifecycle coverage passed in 26 progress/MCP tests. |
| F-029 | I-029 | P1 | U-009 | done | nature_context preserves full structured memory errors after progress commit; facade regression passed. |
| F-030 | I-030 | P2 | U-009 | done | new memory/facade MCP tools require project_root; missing-root regression passed. |
| F-031 | I-031 | P2 | U-009 | done | real JSON-RPC remember/recall/show/forget/all-workflows calls passed. |
| F-032 | I-032 | P1 | U-010 | done | design/requirements approval text synchronized, user approval recorded, approve freeze clean and task plan hash preserved. |
| F-033 | I-033 | P1 | U-010 | done | Agent eval runs new->remember/skip->fresh subprocess resume->recall->cite contract. |
| F-034 | I-034 | P1 | U-010 | done | deterministic eval materializes 100 records across active shared/local/archived/superseded coverage and 0/1/2 metadata. |
| F-035 | I-035 | P2 | U-010 | done | benchmark reports canonical metrics, bytes, cold/warm timings and Python/OS/CPU metadata. |
| F-036 | I-036 | P2 | U-010 | done | separate-process CAS test passed; symlink tests are explicitly skipped only when Windows privilege is unavailable. |
| F-037 | I-037 | P2 | U-010 | done | orchestrator evidence documentation now uses stable memory.md#nm_<uuid4> locators. |
| F-038 | I-038 | P1 | U-008 | done | local migration refuses unignored .nature-memory.bak before writing; regression test passed. |

## Deferred Issues

- n/a
