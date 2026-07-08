# Default stance and red lines

Use this skill to turn the upstream literature library and the confirmed review topic into a small,
high-quality benchmark review-corpus, then deep-learn that corpus and convert the learning into
classification guidance for the downstream screening/classifier step.

The benchmark corpus is a **learning reference, not a source to copy from**. The goal is to understand how
the strongest reviews in this field are built — their framework, narrative logic, writing style, figure
layout, and figure-text relationship — so the user's own review can be planned and its literature
classified, not to reuse any review's actual content.

## Default stance

- Select the ~10 reviews that best match the confirmed topic and have the highest journal impact / article
  quality. Rank by **topical fit first, then journal/article quality**.
- If fewer than 10 suitable reviews exist, keep the maximum available number and record the reason; do not
  pad the corpus with weak matches to reach 10.
- Build the benchmark corpus from the upstream screened library and the confirmed topic — not from memory
  or a fresh unscoped search.
- Import the corpus into Zotero and keep Zotero the single source of truth for the collection and its PDF
  attachments. Follow the import fallback ladder in `workflow.md`.
- Deep-learn at the full-text level **only** the PDFs the user has actually obtained. Wait for the user's
  reply before reading.
- Learn structure, narrative, section rhythm, evidence organization, and figure/table strategy only.
- Verify dynamic journal metrics (impact factor, JCR quartile, CiteScore, APC, scope) from authoritative or
  traceable sources at use time; mark anything unverifiable as `需要人工核查`.
- Preserve real bibliographic metadata. If a field is missing, leave it blank or mark it
  `缺失/需要人工核查`; do not fill it with a plausible value.

## Red lines / Prohibited

- Do not fabricate literature, DOIs, PMIDs, authors, titles, journals, years, abstracts, impact factors,
  quartiles, citation counts, or authorization/access status.
- Do not state journal metrics or a paper's authorization status from memory. Dynamic facts (journal
  scope, IF, quartile, APC, submission rules, license) must be verified live.
- Do not copy titles, section headings/subheadings, paragraphs, figures, tables, or viewpoints from any
  benchmark review. Learn strategy only; never lift content.
- Do not analyze at the full-text level any PDF the user has not obtained, and never claim to have read a
  PDF that was not actually read.
- Do not use or recommend Sci-Hub, piracy, paywall-bypass routes, or unauthorized bulk downloading.
- Do not ask the user for Zotero passwords, institutional passwords, tokens, cookies, or private
  credentials.
- Do not do the downstream job: no large-scale raw-article screening, no formal 2/3-level classification of
  the full library, no full-text evidence extraction, and no manuscript drafting. Produce guidance only.

## Source hierarchy

Use sources in this order:

1. The upstream artifacts: the screened/exported literature library and the confirmed review topic,
   rationale, and research gap.
2. Structured bibliographic metadata: Crossref, PubMed/NCBI E-utilities, DOI metadata, and database tags
   (document type, MeSH terms).
3. Official publisher / journal pages for identity and current metrics.
4. The legally obtained benchmark PDFs for full-text structural learning.

If the upstream literature library is missing, route back to the search/screening step. If the confirmed
topic is missing, route back to the topic step. If a metric or policy may have changed, verify the current
journal page before finalizing.
