# Workflow

Run these steps in order. Each step names the concrete file(s) it produces, so a caller — or
`nature-orchestrator` when it delegates this step — can pick one as `--evidence`. Set an output
directory (default `nature-screening-output/`) and write every derived file under it; keep the raw
export files outside it, unchanged.

## 1. Inventory the inputs

Confirm the required inputs are present without modifying them:

- raw export files (`.ris`, `.nbib`, `.bib`, `.csv`, `.txt`, or spreadsheets from PubMed, Web of
  Science, Scopus, or another discipline-appropriate database);
- the confirmed review topic and research gap;
- the final search strategy and the benchmark-review writing framework / classification guidance.

If exports are missing, ask for the export step's output. If the confirmed topic is missing, ask for
it. If the search strategy is missing but records and topic exist, mark it `需要人工核查` and ask
only for the smallest item needed to continue.

**Product:** `输入/上游输入文件清单.md` — a list of the input files and their paths (raw exports are
referenced, never copied over or edited).

## 2. Normalize metadata into a screening table

Parse the exports into one working table, one row per record, with the fields that are available:
record ID, source database, export filename, DOI, PMID, PMCID, WoS accession number, title,
abstract, authors, year, journal/source, volume/issue/pages/article number, publication type,
language, keywords/MeSH/author-keywords, affiliations, URL, plus the working columns filled by later
steps (duplicate group ID, relevance score, relevance level, matching evidence, retention status,
library inclusion, second-level category, third-level category, target collection path, import
batch, screening status, screening/classification/manual-check reasons, notes).

Never fabricate a missing field; leave it blank or mark `缺失/需要人工核查`.

**Product:** `输出/筛选结果总表.csv`.

## 3. Deduplicate conservatively

Detect duplicates with exact identifiers before any fuzzy matching:

1. exact DOI; 2. exact PMID or PMCID; 3. exact WoS accession number; 4. same normalized title + same
first author + year; 5. highly similar normalized title + matching journal/year, only when the match
is obvious.

For each duplicate group keep one master record (prefer the most complete metadata; preserve all
source identifiers in its notes). Do not delete originals; record the duplicates. If duplicate status
is uncertain, mark `待人工核查` and do not merge.

**Products:** `输出/重复文献记录.csv` (or a duplicate-group column in the screening table) and
`过程记录/去重报告.md`.

## 4. Set discipline-specific matching criteria

Before ranking, write down the title/abstract matching rules derived from the declared discipline and
research direction, the calibrated keywords/search strategy, the confirmed topic and research gap,
and the benchmark-review framework. State the field-specific core object explicitly so the ranking is
reproducible and not biomedical-by-default.

**Product:** a "matching criteria" section in `过程记录/文献筛选日志.md`.

## 5. Rank records by relevance

Score every deduplicated record against the criteria and assign one relevance level (`强相关` /
`中等相关` / `弱相关/排除` / `待人工核查`), with the title/abstract evidence for the decision.
Rank by direct match to the core object, relevance to the review question/gap, fit with the writing
framework and classification guidance, alignment with calibrated terms, and presence of usable
title/abstract evidence; use recency and evidence value only as tie-breakers.

**Products:** `输出/相关性排序表.csv` and `输出/待人工核查文献.csv`.

## 6. Retain the top strongly-relevant set

Keep the top strongly-relevant records for the library (default target 500). If fewer than the target
are `强相关`, keep all `强相关` records and record the actual count. Do not pad with weaker records.
Name the retained library `XXXXX综述文献库`, where `XXXXX` is a concise Chinese topic name
(6–15 characters, no filename-unfriendly characters).

**Products:** `输出/强相关前500文献.csv` and `输出/纳入文献列表.csv`;
`输出/排除文献列表.csv` for the rest.

## 7. Build the second/third-level classification

Design the category tree from the benchmark-review writing framework, then adapt labels to the actual
records and discipline. Default second-level candidates (adapt, do not force biomedical labels):

- `01-背景与概念基础`
- `02-核心理论/机制/原理`
- `03-关键方法/技术/模型`
- `04-对象/系统/场景/证据`
- `05-指标/表征/评价体系`
- `06-设计/优化/干预/解决策略`
- `07-转化/工程实现/应用`
- `08-争议/局限/研究空白`
- `09-方法学/平台/数据与工具`
- `10-综述与指南背景文献`
- `99-待人工核查`

Create third-level subcategories under each as the records require.

**Product:** `输出/XXXXX综述文献库/二级三级分类表.csv`.

## 8. Assign every retained record

Place each retained record in exactly one primary second-level category and one third-level
subcategory, or in `99-待人工核查`. Record optional secondary categories in the mapping table. Give
a screening status (`纳入` / `排除` / `待人工核查`) and a specific reason for every excluded and
uncertain record.

**Product:** updated `输出/XXXXX综述文献库/二级三级分类表.csv` with every retained record assigned.

## 9. Prepare the reference-manager import mapping

Generate the handoff so the next step can import the library and preserve the tree as far as
possible: a folder tree of category-specific reference files, an import mapping table, and a
collection-structure listing. Classified RIS/reference files are derived; raw exports stay unchanged.
Do not promise that every importer recreates the hierarchy — the mapping table and folder tree are
authoritative.

**Products:** `输出/XXXXX综述文献库/XXXXX综述文献库.ris`,
`输出/XXXXX综述文献库/Zotero导入映射表.csv`,
`输出/XXXXX综述文献库/Zotero集合结构清单.md`, and the classified reference files under
`输出/Zotero导入文件/XXXXX综述文献库/<category>/`.

## 10. Write logs and quality checks

Finish the process records and run the quality gate before handing off.

**Products:** `过程记录/文献筛选日志.md`, `过程记录/分类日志.md`,
`质量核查/筛选分类质量核查.md`, `质量核查/Zotero导入准备核查.md`.

## Quality gate

Before reporting, verify: inputs and paths recorded; discipline and direction recorded and screening
moved broad → precise; no biomedical-only assumptions on non-biomedical topics; metadata normalized
without fabrication; deduplication decisions and uncertain groups recorded; every deduplicated record
has a relevance level or an uncertainty reason; the top strongly-relevant set is retained (or the
actual count is recorded); the library is named `XXXXX综述文献库`; second/third-level categories
exist; every retained record has a third-level category or `99-待人工核查`; inclusion/exclusion/
manual-check reasons recorded; import mapping and classified files generated; the collection-structure
listing describes the intended hierarchy; raw exports remain unchanged.

## Report

Follow `core/output-contract.md` for the deliverable file set and the user-facing report format.
Report the absolute path of each deliverable so the caller can use one (typically
`输出/XXXXX综述文献库/二级三级分类表.csv` or `输出/纳入文献列表.csv`) as `--evidence`.
