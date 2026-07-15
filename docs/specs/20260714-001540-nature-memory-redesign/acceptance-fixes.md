# Acceptance Fixes

> **Source:** E:/CodeProject/Useful-marketplace/docs/specs/20260714-001540-nature-memory-redesign/acceptance_state.json
> **Round:** 3
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
| F-039 | I-039 | P2 | U-001 | done | unique alias/title matching now fails closed; alias-title regression passed |
| F-040 | I-040 | P2 | U-001 | done | show resolves requested valid entry and returns unrelated diagnostics; mixed-schema regression passed |
| F-041 | I-041 | P2 | U-001 | done | stable touch rewrites canonical updated_at without changing ID; regression passed |
| F-042 | I-042 | P1 | U-002 | done | local migration backup uses exclusive create and rejects hardlink/existing destination; regression passed |
| F-043 | I-043 | P2 | U-002 | done | directory memory paths return memory_path_not_regular_file structured errors |
| F-044 | I-044 | P2 | U-002 | done | symlink boundary has executable OS test plus deterministic Windows fallback branch; safety suite passed |
| F-045 | I-045 | P2 | U-002 | done | ignored local success and forced Git failure regressions passed |
| F-046 | I-046 | P1 | U-003 | done | final CAS check is co-located with atomic replacement and external rewrite remains intact; regression passed |
| F-047 | I-047 | P2 | U-003 | done | fcntl lock backend harness exercised flock acquire/release; concurrency suite passed |
| F-048 | I-048 | P1 | U-004 | done | remember supersedes transitions all referenced active sources to superseded; regression passed |
| F-049 | I-049 | P2 | U-004 | done | stable memory locator is accepted by show and recall; regression passed |
| F-050 | I-050 | P2 | U-004 | done | real JSON-RPC supersede call covered by MCP lifecycle suite |
| F-051 | I-051 | P2 | U-005 | done | active count over 12 is advisory and check remains successful |
| F-052 | I-052 | P3 | U-005 | done | singleton consolidate plan rejects source_ids_required |
| F-053 | I-053 | P3 | U-005 | done | soft-byte and hard consolidate budget paths covered by regression |
| F-054 | I-054 | P2 | U-006 | done | stable touch returns deprecated compatibility fields |
| F-055 | I-055 | P1 | U-007 | done | recall requires_live_verification filter enforced and tested |
| F-056 | I-056 | P2 | U-007 | done | list accepts explicit local scope and reports scope in output |
| F-057 | I-057 | P2 | U-008 | done | migration collision error preserves collisions, scope, path and current ETag context |
| F-058 | I-058 | P2 | U-008 | done | MCP migrate schema conditionally requires workflow_dir unless all_workflows=true |
| F-059 | I-059 | P2 | U-008 | done | real JSON-RPC migrate dry-run covered in all-tools smoke |
| F-060 | I-060 | P2 | U-008 | done | real per-workflow facade/migration recovery and partial lifecycle paths covered |
| F-061 | I-061 | P1 | U-009 | done | facade review preserves structured memory error context after progress commit |
| F-062 | I-062 | P1 | U-009 | done | facade complete/block require explicit workflow_dir in schema, dispatch and implementation |
| F-063 | I-063 | P2 | U-009 | done | real JSON-RPC resume/complete/block and missing-workflow recovery covered |
| F-064 | I-064 | P1 | U-010 | done | recall fixture contains exact partial mixed no-hit slices with relevance 0/1/2 |
| F-065 | I-065 | P2 | U-010 | done | deterministic benchmark now records 256 KiB single workload, 12000 all-workflow records, warm/p95 and recall |
| F-066 | I-066 | P2 | U-010 | done | cross-platform symlink fallback and fcntl execution evidence added |
| F-067 | I-067 | P2 | U-010 | done | MCP JSON-RPC smoke exercises all 24 declared tools |
| F-068 | I-068 | P2 | U-010 | done | secret documentation distinguishes hard-rejected known formats from warning-only suspicious assignments |
| F-069 | I-069 | P1 | U-010 | done | agent eval executes independent fixture actions and counts unauthorized writes explicitly |
| F-070 | I-070 | P1 | U-010 | done | current worktree full verification refreshed: 120 tests, compile, JSON, deterministic and agent evals, diff check |
| F-071 | I-071 | P2 | U-002 | done | all-workflows no longer skips directory-valued memory paths and returns structured malformed-path diagnostics |
| F-072 | I-072 | P2 | U-001 | done | same-title show regression passes: valid stable ID succeeds while unrelated unknown-schema diagnostic remains in returned diagnostics |
| F-073 | I-073 | P2 | U-001 | done | legacy show regression passes and returns preserved updated timestamp |
| F-074 | I-074 | P1 | U-002 | done | Windows hardlink regression plus WSL safety suite pass; canonical memory hardlinks are rejected before read |
| F-075 | I-075 | P2 | U-002 | done | all-workflow check/list/recall/migrate/index scan diagnostics preserve unsafe path errors instead of silently skipping |
| F-076 | I-076 | P2 | U-002 | done | nonexistent project root recall returns structured project_root_not_found |
| F-077 | I-077 | P1 | U-003 | done | final CAS regression passes on Windows and WSL rename-exchange path preserves external rewrite |
| F-078 | I-078 | P2 | U-003 | done | os.replace PermissionError is converted to retryable replace_failed |
| F-079 | I-079 | P2 | U-003 | done | real WSL Unix fcntl lock test passes; mocked backend remains separate compatibility coverage |
| F-080 | I-080 | P2 | U-003 | done | forced backend EPERM regression returns lock_unavailable rather than lock_timeout |
| F-081 | I-081 | P1 | U-004 | done | update-time supersedes regression transitions referenced active source to superseded |
| F-082 | I-082 | P2 | U-004 | done | cross-workflow locator regression returns locator_workflow_mismatch |
| F-083 | I-083 | P3 | U-004 | done | lifecycle and locator regressions cover update supersedes, mismatched locator, title/entry lookup and successor behavior |
| F-084 | I-084 | P2 | U-005 | done | budget regression confirms archived entries do not count toward max_entries |
| F-085 | I-085 | P3 | U-005 | done | consolidate apply singleton regression returns source_ids_required |
| F-086 | I-086 | P3 | U-005 | done | soft_active_bytes warning and hard-budget boundary regressions pass |
| F-087 | I-087 | P1 | U-006 | done | AGENTS backup hardlink/exclusive-create regression returns agents_backup_exists without modifying external target |
| F-088 | I-088 | P1 | U-007 | done | nature_progress_server.py now requires workflow_dir unless all_workflows=true; test_nature_progress_server.py (6 tests OK) covers schema and omitted-workflow dispatch. |
| F-089 | I-089 | P1 | U-008 | done | migration dry-run detects legacy-alias versus canonical-title collision |
| F-090 | I-090 | P1 | U-008 | done | migration all regression reports invalid directory and still migrates valid workflow |
| F-091 | I-091 | P2 | U-008 | done | forced post-backup replace failure removes operation-created backup and retry succeeds |
| F-092 | I-092 | P2 | U-008 | done | migration partial/recovery and real MCP migration tests pass |
| F-093 | I-093 | P1 | U-009 | done | nature_memory_check/list dispatch no longer broadens omitted workflow_dir; test_nature_progress_server.py (6 tests OK) covers fail-closed behavior. |
| F-094 | I-094 | P2 | U-009 | done | nature_context partial responses now preserve parser error diagnostics and structured memory_parse_errors; test_nature_progress.py (25 tests OK) covers duplicate-id mixed memory. |
| F-095 | I-095 | P1 | U-010 | done | nature_memory_eval.py agent mode records fixture policy prompt, tool trace, model metadata, project snapshots, and reviewer checks; agent eval 20 scenarios x 3 fresh processes passed with unauthorized writes/tool calls 0. |
| F-096 | I-096 | P1 | U-010 | done | deterministic eval now gates exact/partial/mixed/no-hit slices plus scope/lifecycle/fixture coverage; deterministic eval and eval regression tests passed. |
| F-097 | I-097 | P1 | U-010 | done | lock hardlink pre-open rejection and workflow lock safety regressions pass |
| F-098 | I-098 | P2 | U-010 | done | deterministic benchmark now materializes canonical memory.md files: physical single workflow 262144 bytes and 1000 workflows/12000 records; canonical benchmark gates passed. |
| F-099 | I-099 | P2 | U-010 | done | real Unix fcntl and symlink tests run in WSL (16 tests OK); Windows host probe reports symlink privilege unavailable explicitly, with no false pass claim; README documents host-scoped evidence. |
| F-100 | I-100 | P2 | U-010 | done | eval README explicitly labels agent mode offline fixture-policy evidence and separates it from connected model evaluation; trace/reviewer scope is documented. |
| F-101 | I-101 | P2 | U-003 | done | stale ETag error includes workflow, scope, entry ID, current/expected ETag and repair guidance |
| F-102 | I-102 | P2 | U-007 | done | recall MCP schema and dispatch share explicit workflow/all_workflows conditional selection; schema and dispatch regression tests passed. |
| F-103 | I-103 | P2 | U-007 | done | repeated CJK bigram scoring is deduplicated and exact precedence regression passes |
| F-104 | I-104 | P2 | U-007 | done | bounded recall fallback reconsiders candidates with complete compact records under legal 4096-byte budget |
| F-105 | I-105 | P3 | U-007 | done | MCP recall validates top_k/max_bytes before empty all-workflow roots; server regression test rejects top_k=6. |
| F-106 | I-106 | P1 | U-008 | done | migrate conditional schema now requires all_workflows in its if branch, so omitted all_workflows correctly selects workflow_dir path; schema/dispatch regression tests passed. |

## Deferred Issues

- n/a
