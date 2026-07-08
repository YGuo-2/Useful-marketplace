# Default stance and source hierarchy

Use this skill to turn a raw literature export into a defensible, reference-manager-ready review
library: a deduplicated and relevance-ranked record table, a retained set of the strongest
topic-matched records, a second-level/third-level category tree, and an import mapping for the next
step. The core purpose is **not** PDF acquisition; it is to keep the strongest topic-matched records
and organize them by the benchmark-review writing framework.

This skill fuses SCI从0-1workflow step `06-SCI文献筛选分类器`. It runs after the review topic and
benchmark framework are fixed, and it hands off a classified library that a later step can import
into Zotero and use to fetch PDFs.

## Default stance

- **Discipline-agnostic.** Support medicine, life sciences, engineering, materials, chemistry,
  physics, computer science, environmental science, agriculture, management, social science, and
  interdisciplinary topics. Do not assume the project is biomedical.
- **Broad to specific.** Screen through a funnel: start from the declared discipline and research
  direction, narrow to the calibrated keywords and search strategy, then to the confirmed topic and
  research gap, then to the benchmark-review framework — and only then judge each record.
- **Field-appropriate "core object."** Terms such as disease, patient, mechanism, pathway,
  biomarker, and clinical translation are valid only for biomedical/life-science projects. For other
  fields use the corresponding object: material, structure, device, process, algorithm, model,
  architecture, system, dataset, sensor, catalyst, energy-storage mechanism, manufacturing method,
  environmental scenario, policy setting, management construct, or application domain.
- **Conservative by default.** When a duplicate, a relevance level, or a category is uncertain, mark
  it `待人工核查` rather than forcing a decision.
- **Evidence over volume.** Retain the top strongly-relevant records; if fewer than the target
  exist, keep all strongly-relevant records and record the actual count. Never pad the library with
  weakly-related records to reach a number.
- **Non-destructive.** Treat the raw export files as read-only. Every classified/derived file is a
  new artifact; the originals stay byte-for-byte unchanged.
- **Stay in lane.** This skill screens and classifies. It does not download PDFs, operate Zotero,
  read full text, extract formal evidence, or write manuscript prose.

## Relevance levels

Use these four levels consistently for every deduplicated record:

- `强相关` — title/abstract directly matches the review topic within the selected discipline and is
  likely to support the review's main sections.
- `中等相关` — partially related, not central, or supports only background/context.
- `弱相关/排除` — outside the core topic, wrong discipline/object/method/system/population/scenario,
  or unrelated to the review question.
- `待人工核查` — metadata is insufficient or the topic fit is genuinely ambiguous.

## Source hierarchy

Use sources in this order:

1. The user's own exported records and the confirmed topic, research gap, search strategy, and
   benchmark-review framework from upstream steps.
2. Structured bibliographic identifiers already inside the export: DOI, PMID, PMCID, Web of Science
   accession number.
3. Publisher / index pages, only to confirm a record's identity or resolve a duplicate — not to add
   records that were never exported.

## Prohibited — red lines

- **Do not fabricate** DOIs, PMIDs, PMCIDs, WoS numbers, titles, abstracts, authors, journals,
  years, or any other citation metadata. Leave a missing field blank or mark it
  `缺失/需要人工核查`. Never invent journal impact factors, quartiles, or indexing status.
- **Do not mark anything unverifiable as verified.** Any claim, metadata field, or duplicate/relevance
  decision you cannot substantiate from the export or a checked source is labelled `需要人工核查`.
- **Do not answer dynamic facts from memory.** Journal scope, impact factor, quartile/partition, APC,
  submission or licensing rules change over time; if a screening decision depends on one, verify it
  online at use time and cite where you checked, or defer it to `需要人工核查`.
- **Do not delete original duplicate records**, and do not modify the raw export files. Duplicates
  are recorded in a derived file, never removed from the source.
- **Do not merge uncertain duplicates.** If duplicate status is not obvious from exact identifiers or
  a clear title+author+year match, keep both and mark `待人工核查`.
- **Do not pad to the retention target** with `中等相关` or `弱相关/排除` records.
- **Do not force biomedical vocabulary or categories** onto engineering, materials, computer science,
  environmental, management, social-science, or other non-biomedical topics.
- **Do not leave any retained record unclassified.** Every retained record gets one third-level
  category or is placed in `99-待人工核查`.
- **Do not promise perfect Zotero hierarchy from RIS alone.** RIS cannot always encode a collection
  tree; the mapping table and folder tree are the authoritative handoff.
