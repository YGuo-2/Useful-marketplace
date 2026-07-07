# Stance and topic pattern (topic & research-gap)

Use this step to turn the exported RIS/reference records from the upstream search into decision-ready
review-topic options grounded in real literature:

- an integrated year–title–abstract analysis table over the export
- topic clusters with the research gap each one exposes
- three candidate review topics (稳妥 / 平衡 / 高冲击) plus one recommended option

This is the topic-selection and research-gap step. It is **analysis for a decision**, not formal literature
screening, PDF retrieval, search-string regeneration, or manuscript writing.

## Default stance

- Candidate topics must be shaped by the exported year–title–abstract evidence, not by rephrasing keywords
  or imagining a field from memory.
- Prefer real, repeated literature patterns over broad "hot topic" impressions.
- Every candidate must be specific enough to write a defensible review around, and honest about its
  evidence risk.
- Keep dynamic facts (target-journal tier / 分区, impact factor, scope, submission rules) out of memory:
  verify online when they gate a recommendation, otherwise flag them.

## Fixed topic pattern

Every candidate topic must follow this pattern:

```text
研究对象 + 核心机制/关键变量 + 临床或科学问题 + 综述视角
```

For every candidate, explicitly define:

1. 研究对象 — disease, population, cell type, molecular axis, material, technology, intervention,
   biomarker, or clinical scenario.
2. 核心机制或科学问题 — e.g. immune regulation, inflammatory pathway, metabolic reprogramming,
   microenvironment interaction, resistance mechanism, diagnostic prediction, treatment response, tissue
   repair, toxicity, or clinical translation.
3. 综述切入角度 — exactly one of: 机制型 / 临床转化型 / 诊疗策略型 / 生物标志物型 / 技术方法型 /
   争议整合型 / 未来方向型.
4. 具体研究空白 — e.g. mechanism chain not yet closed, basic mechanism disconnected from clinical evidence,
   conflicting conclusions across studies, thin evidence for a subtype / population / scenario, no unified
   classification framework, no mechanism-to-intervention integration, or no prediction / stratification /
   efficacy-evaluation system.
5. 目标分区适配 — if the target is Top 一区 / JCR Q1, the topic needs stronger mechanism depth, frontier
   value, controversy, translational potential, or framework-building value.

## Prohibited / red lines

- Do not produce broad, vague titles. Anti-example: `肠道菌群与肿瘤免疫治疗研究进展`. A title with no
  mechanism / variable, no specific question, and no review angle is not acceptable.
- Do not fabricate specific papers, authors, DOI, PMID, journal statistics, impact factors, or citation
  counts. Cluster patterns are described in aggregate from the export, never as invented individual
  references.
- Do not claim a final number of included studies — that belongs to a later screening step.
- Do not silently choose one topic. Emit all three candidates with a recommendation and let
  nature-orchestrator run the decision.
- If the export is missing, route back to the search step; if metadata is incomplete, mark the affected
  items `需要人工核查` rather than guessing.
- Do not assert dynamic journal facts (分区 / IF / scope / APC / submission or licensing rules) from memory;
  verify online or flag `需要人工核查`.

## Source basis

Fused from the SCI workflow step `04-SCI选题与研究空白识别`. The governing discipline is unchanged:
candidate topics and gap comparisons are derived only from exported records, and evidence limits are marked,
never invented.
