# Nature memory evaluation

The fixtures are versioned with the memory contract:

- `fixtures/recall_cases.json`: 5 workflows, 80 records, and 50 graded queries.
- `fixtures/agent_scenarios.json`: 20 durable-write / no-write scenarios.

Run the deterministic scorer:

```text
python plugins/nature-workflow/evals/nature_memory_eval.py --mode deterministic
```

It reports Recall@3, MRR, nDCG@3, no-hit FPR, a single-workflow benchmark, and a 1000-workflow / 12000-record parsing benchmark. The thresholds are the approved design thresholds: Recall@3 >= 0.95, MRR >= 0.90, nDCG@3 >= 0.85, and no-hit FPR <= 0.10.

Run the fresh-process contract harness:

```text
python plugins/nature-workflow/evals/nature_memory_eval.py --mode agent --runs 3
```

This is an offline deterministic fixture harness, not a connected model evaluation. Each case launches a new Python process and creates a fresh temporary project. It checks durable write precision/recall, locator validity, must-not-write boundaries, and zero security/privacy failures. Connected model results must carry their own model, tool, prompt, project snapshot, and reviewer evidence.
