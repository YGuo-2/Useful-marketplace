# Nature memory evaluation

The fixtures are versioned with the memory contract:

- `fixtures/recall_cases.json`: 5 workflows, 80 active shared records, lifecycle/local coverage, and 50 graded queries.
- `fixtures/agent_scenarios.json`: 20 durable-write / no-write scenarios with fixed expected locator IDs for durable entries.

Run the deterministic scorer:

```text
python plugins/nature-workflow/evals/nature_memory_eval.py --mode deterministic
```

The scorer reports overall Recall@3, MRR, nDCG@3, and no-hit FPR, plus exact/partial/mixed/no-hit slice metrics and gates. Scope and lifecycle checks, the canonical benchmark workload, and the approved thresholds are part of the pass result: Recall@3 >= 0.95 for each lexical slice, MRR >= 0.90, nDCG@3 >= 0.85, and no-hit FPR <= 0.10. The benchmark uses a canonical 256 KiB `memory.md` and a canonical 1000-workflow / 12000-record workload, with five warm-run median/p95 measurements.

Run the fresh-process contract harness:

```text
python plugins/nature-workflow/evals/nature_memory_eval.py --mode agent --runs 3
```

This is an offline deterministic admission-policy harness, not a connected model evaluation. The local policy derives `remember` or `skip` from the scenario prompt/body; it does not read a gold action map to decide whether to write. Each case launches a new Python process, uses a fresh temporary project, and records the prompt, model metadata, allowed tools, tool trace, before/after project snapshots, and deterministic reviewer checks. Durable scenarios use fixed expected locator IDs and validate the citation in a separate fresh process; no-write scenarios explicitly assert that citation is not applicable. The harness checks durable-write precision/recall, expected locator validity, must-not-write boundaries, unauthorized tool calls, and zero security/privacy failures. Connected model results must carry their own model, tool, prompt, project snapshot, and reviewer evidence.

The output also records real host probes for symlink containment and the Unix `fcntl` lock backend. A foreign-platform probe marked unavailable or not applicable is not counted as passed; full cross-platform evidence requires running the same tests on the relevant Windows and Unix environments. Mocked backend tests remain compatibility regressions and are not cross-platform evidence.
