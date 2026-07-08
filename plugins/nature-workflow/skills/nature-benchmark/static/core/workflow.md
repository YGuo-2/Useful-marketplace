# Workflow

Run these steps in order for any benchmark-corpus job. A later step must not silently repair missing
evidence from an earlier one. Every step names the artifact it writes so the orchestrator can record a
concrete `--evidence` path.

## 1. Confirm inputs and folders

- Confirm the upstream inputs: the screened/exported literature library and the confirmed review topic,
  rationale, and research gap. If the library is missing, route back to search/screening; if the topic is
  missing, route back to the topic step.
- Preserve upstream raw files unchanged and record their paths.
- Remind the user in the working language to open Zotero and keep it open through import, PDF acquisition,
  and PDF inspection.

Artifact: `输入/上游输入文件清单.md` (upstream input inventory).

## 2. Identify review articles

- Identify reviews in the upstream library using publication type, title/abstract signals, database tags,
  MeSH terms, document-type fields, and journal metadata.
- Do not add reviews that are not in the upstream library.

Artifact: notes in `过程记录/对标综述检索与筛选日志.md`.

## 3. Rank candidates

Rank by topical fit first, then journal/article quality, using a transparent scoring table.

Topical fit (first):

- direct match with the confirmed review topic;
- same review type, research object, model, mechanism, pathway, exposure, intervention, or methodological
  scope;
- same review angle and research gap;
- strong title/abstract overlap with the confirmed topic.

Journal impact and article quality (second):

- verify current journal metrics (IF, JCR quartile, CiteScore) from authoritative/traceable sources when
  they affect ranking; mark unverifiable metrics `需要人工核查`;
- prefer recent, high-quality reviews (systematic, authoritative narrative, consensus/guideline-linked, or
  high-impact-journal reviews);
- consider citation influence, publication year, journal fit, review depth, figure quality, and conceptual
  clarity.

Do not fabricate any metric or bibliographic field.

Artifact: `输出/对标综述排序表.csv`.

## 4. Select the benchmark corpus

- Select the 10 best benchmark reviews. If fewer than 10 suitable reviews exist, keep the maximum available
  number and record the reason.
- Write the selection rationale (why each was included, its match basis, and its journal/article-quality
  basis).

Artifact: `输出/对标综述筛选理由.md`.

## 5. Export the benchmark RIS

- Export or generate RIS records for the selected reviews into `输出/对标综述文献库RIS/` (a combined
  `对标综述文献库.ris` plus per-item RIS when useful).
- Preserve real metadata; leave missing fields blank or marked `缺失/需要人工核查`.

Artifact: `输出/对标综述文献库RIS/对标综述文献库.ris`.

## 6. Import into Zotero (fallback ladder)

Try in this priority order and record the result at each rung:

1. **Zotero plugin/connector (primary):** confirm Zotero is open, create/select a collection named
   `对标综述文献库`, import the RIS, and confirm imported records match the selected list.
2. **Computer Use (fallback):** only after recording why the plugin/connector was unavailable or failed —
   focus Zotero, create/select the collection, import the RIS, confirm the match.
3. **Manual boxed prompt (last resort):** if neither can complete the import reliably, show the user a boxed
   prompt asking them to open Zotero, keep it open, import the `对标综述文献库RIS` folder, obtain PDFs, and
   reply when done.

Never request Zotero or institutional credentials.

Artifact: `输出/Zotero导入记录.md`.

## 7. Wait for PDF acquisition

- Ask the user to acquire PDFs in Zotero for all or part of the benchmark reviews and to reply when
  finished. If import succeeded but PDFs are still missing, show a boxed prompt asking for manual PDF
  acquisition in Zotero.
- Do not proceed to full-text learning until the user replies. Record each review's PDF status.

Artifact: `输出/对标综述PDF状态表.csv`.

## 8. Deep-read obtained PDFs

- Prefer the Zotero connector/plugin to locate attached PDFs; fall back to local exports, user-provided
  paths, or Computer Use.
- Read every **available** PDF page by page, beginning to end (visual inspection for scanned/image-heavy
  PDFs). Analyze at the full-text level only PDFs actually obtained; never claim to have read a PDF you did
  not read.
- Learn: title strategy and topic positioning; abstract structure; main heading architecture; section order
  and argument progression; how mechanisms, clinical evidence, controversies, limitations, and future
  directions are arranged; figure types/placement and figure-text relationship; table/evidence-summary
  strategy; writing tone, information density, transition style, and claim strength; how uncertainty and
  research gaps are presented.
- Learn strategy only — never copy titles, headings, prose, figures, tables, or viewpoints.
- If full-text reading changes the article-quality judgment, rerank the corpus.

Artifacts: `输出/对标综述整理素材库.md`, `输出/对标综述深度学习报告.md`, and
`过程记录/PDF阅读学习日志.md`.

## 9. Produce the handoff

- Summarize a proposed title direction and writing framework for the user's review.
- Convert the learning into the downstream classification guide, especially the suggested second-level and
  third-level classes and the rationale; mark unresolved items `需要人工核查`.

Artifacts: `输出/拟定标题与写作思路.md` and `输出/下一步文献分类指导框架.md`.

## 10. Report

Return the report described in `output-contract.md`, putting the two evidence paths — the benchmark-corpus
report (`对标综述深度学习报告.md`) and the classification guide (`下一步文献分类指导框架.md`) — where the
orchestrator can record them with `complete --evidence`.
