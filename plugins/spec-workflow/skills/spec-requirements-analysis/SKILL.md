---
name: spec-requirements-analysis
description: >
  Use before Spec workflow artifact generation to run Kiro-style Analyze Requirements
  across ambiguity, conflicts, missing boundaries, undefined concepts, failure paths,
  permissions, concurrency, data consistency, and risk checks. Results must be
  recorded inside product.md or requirements.md rather than a standalone file.
---

# Spec workflow Requirements Analysis

Use this as the Kiro-style Analyze Requirements step before generating or finalizing Requirements-First `product.md` or Design-First `requirements.md`.

## Hard Rules

- Do not create `<specs_dir>/analysis.md` by default; carry the results into `product.md` or `requirements.md`.
- Do not use this as approval. Passing analysis does not authorize implementation.
- Quick Plan may skip the full analysis only for low-risk work with explicit human authorization, and the skip reason must be recorded.
- If analysis discovers conflicting requirements or missing high-risk boundaries, stop spec generation and ask focused clarification questions.
- Intake handoff items must be classified into the analysis. Do not drop accepted assumptions, unresolved risks, non-goals, or decision boundaries when moving from intake to `product.md` or `requirements.md`.

## Analysis Checklist

Check and record:

- ambiguous wording, undefined concepts, and unclear actors
- conflicting functional or non-functional requirements
- intake assumptions, accepted unknowns, non-goals, and decision boundaries
- missing acceptance criteria or non-testable criteria
- empty states, invalid inputs, failure paths, retry behavior, and rollback expectations
- permissions, authorization, privacy, sensitive data, and security boundaries
- concurrency, data consistency, cache consistency, and migration risks
- compatibility, public contract, and rollout constraints

## Output Contract

For Requirements-First, update `<specs_dir>/product.md` with:

```markdown
## Analyze Requirements / 需求分析结论

- **歧义检查：** ...
- **冲突检查：** ...
- **遗漏边界：** ...
- **Intake 未决项归类：** ...
- **并发 / 数据 / 安全风险：** ...
- **Quick Plan 跳过原因：** n/a
```

For Design-First, update `<specs_dir>/requirements.md` with:

```markdown
## Analyze Requirements / 需求分析结论

- **歧义检查：** ...
- **设计一致性：** ...
- **冲突检查：** ...
- **失败路径：** ...
- **Intake 未决项归类：** ...
- **Quick Plan 跳过原因：** n/a
```
