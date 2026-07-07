# Workflow and products

Run these steps once over the exported records. Each step leaves a named product; the final `.md` artifact
is what nature-orchestrator receives as `--evidence`.

## 1. Confirm inputs

- Confirm the exported RIS/reference records from the upstream search step, plus any search/export log,
  research direction, research keywords, and target partition.
- If the export is missing, stop and route back to the search step. If direction or target partition is
  missing, ask for the smallest missing item and proceed after recording it.
- Product: a one-line input inventory (what was found / what is missing).

## 2. Inspect fields

- Parse or inspect year, title, abstract, keywords, journal, DOI, and identifiers when available.
- Product: field-coverage notes; mark absent metadata `需要人工核查`.

## 3. Build the year–title–abstract analysis table

- Integrate the export into the analysis table with columns: 聚类 × 年份趋势 × 代表性标题/摘要模式 ×
  主题信号 × 可能研究空白 × 证据风险 × 需要人工核查.
- Describe patterns in aggregate; do not attach invented individual references.
- Product: the analysis table.

## 4. Cluster and identify gaps

- Group records into preliminary topic clusters from repeated title/abstract patterns.
- Within and across clusters, identify: crowded broad themes; emerging mechanisms / technologies;
  high-value directions; biomarker / diagnosis / intervention / population / model / methodology clusters;
  contradictory findings; and under-synthesized gaps.
- Product: cluster list with the gap each exposes, plus a short cross-cluster gap comparison.

## 5. Derive three candidate topics

- Produce exactly three candidates along the risk axis: A 稳妥型, B 平衡型, C 高冲击型.
- Each candidate follows the fixed topic pattern and defines all five required fields (see `stance.md`):
  研究对象, 核心机制/科学问题, 综述切入角度, 具体研究空白, 目标分区适配 — plus source literature pattern,
  evidence risk, novelty, and writing difficulty.
- Reject any candidate that reduces to a broad title without a mechanism / variable, a specific question,
  and a review angle.
- Product: the candidate-topics table.

## 6. Recommend and hand to the decision

- Mark exactly one recommended option and give a one-sentence reason.
- Note that the user may also modify a candidate or supply a custom topic (D); nature-orchestrator presents
  A/B/C/D under its decision protocol. Do not pick for the user.
- Product: recommended option + reason.

## 7. Write the deliverable

- Write the analysis table, candidate topics, and decision block to a single Markdown file (no docx). See
  `output-contract.md` for the exact structure and suggested filename.
- Product: the `.md` artifact path — this absolute path is the evidence nature-orchestrator completes the
  step with.
