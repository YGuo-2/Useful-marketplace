# Workflow and deliverables

Run the `select` phase (steps 1-8) first. Stop at the decision fork (step 8) and let the orchestrator
present the tiered candidates. Run the `deep-learn` phase (steps 9-12) only after the user confirms a
target journal. Every step names the deliverable it produces; the deliverable paths are the evidence
the orchestrator records with `complete --evidence`.

## Accepted inputs

Completed manuscript draft (required); article type; confirmed topic, research direction, and
keywords; target partition (JCR quartile / CAS zone / custom); OA / APC tolerance; publisher, timeline,
or other preferences; any journals the user already favors. If the draft is missing, route back to the
drafting step. If the target partition or preferences are missing, ask the user to confirm them first.

## Select phase

### 1. Read the draft and extract the manuscript profile

Extract: proposed title, research direction, keywords, discipline, target readership, article type,
main novelty, evidence strength, figure/table completeness, and likely submission risks.
**Deliverable:** a manuscript-profile note (may live inside the process record).

### 2. Match candidate journals

Use journal-finder tools (Elsevier Journal Finder, Springer Journal Suggester, Wiley Journal Finder,
JANE, LetPub, MedSci, or comparable) with the title/abstract/keywords; also search journals that
published similar work in the past 3-5 years and the journal distribution of same-topic papers. Build
an initial candidate list and drop clearly mismatched journals. **Deliverable:** an initial candidate
list (in the process record).

### 3. Verify each candidate on official sources

For every surviving candidate confirm, with an access date: scope match; whether the manuscript's
article type is accepted; SCI/SCIE (or relevant) indexing; JCR quartile; CAS partition; latest impact
factor; CiteScore; publisher; OA status; APC; review/publication timeline; annual article volume; and
whether closely similar work was recently published. Mark unconfirmable items `需要人工核查`.
**Deliverable:** the verified fields feeding the candidate table.

### 4. Score fit on 14 dimensions

Score each candidate 0-5 on: (1) topic fit, (2) discipline-scope fit, (3) target-readership fit,
(4) accepts the article type, (5) recently published similar work, (6) manuscript quality matches
journal level, (7) target-partition fit, (8) evidence strength meets expectations, (9) figure/table
quality fits journal style, (10) novelty sufficiency, (11) submission risk, (12) publication cost,
(13) review timeline, (14) user-preference fit.

Scale: `5` highly matched · `4` well matched · `3` basically matched but risky · `2` weak, not a
priority · `1` clearly mismatched · `0` does not meet submission conditions.
**Deliverable:** per-candidate scores in the candidate table.

### 5. Run the 13-item submission-risk checklist

Check: (1) scope mismatch, (2) article type not accepted, (3) invitation-only, (4) partition/IF below
the user target, (5) APC too high or unclear, (6) timeline too long, (7) abnormal recent article
volume, (8) unstable indexing, (9) warning-list risk, (10) predatory risk, (11) publisher/journal
reputation issue, (12) novelty risk from too many same-topic papers, (13) a highly similar piece
recently published in the candidate. A high-risk journal must not be the top recommendation.
**Deliverable:** `投稿风险核查.md`.

### 6. Stratify into four tiers

- **Tier 1 — 冲刺 (ambitious):** high partition/influence, strong fit, accepts the type, demands high
  novelty and completeness. Suitable when evidence, figures, and writing are strong and the user
  accepts higher rejection risk.
- **Tier 2 — 主投 (primary target):** high fit, partition matches the user target, moderate risk,
  reasonable acceptance odds. This is the highest-priority recommendation.
- **Tier 3 — 稳妥 (safer):** good fit, partition possibly slightly lower, higher acceptance odds.
- **Backup — 保底:** higher acceptance odds, partition/influence possibly lower; still check quality
  and warning-list risk. Never recommend a backup journal as the first choice for a strong manuscript.

**Deliverable:** tier assignment per candidate in the candidate table and report.

### 7. Emit the candidate package

Produce the deliverables in `core/output-contract.md`: `目标期刊候选表.csv`, `目标期刊推荐报告.md`,
`投稿风险核查.md` (from step 5), and `期刊信息来源记录.md` (sources + access dates).
**Deliverable:** the four files above; their paths are the `select` evidence.

### 8. Decision fork — hand tiered candidates to the orchestrator

Present the four-tier spread and the top recommendation with its match points and risk points. Do not
pick the journal yourself. The orchestrator surfaces the options under its decision protocol and waits
for the user to confirm a target journal (or ask for more candidates). **Deliverable:** the confirmed
target journal, recorded as the decision.

## Deep-learn phase (only after the user confirms a target journal)

### 9. Retrieve recent benchmark articles from the confirmed journal

Retrieve 3-5 high-quality articles of the same/similar article type published by the confirmed journal
in the past 3-5 years; rank them by relevance to the manuscript topic. If fewer than 3-5 suitable
articles exist, record the actual number and clearly mark any closely-related fallback sources. Prompt
the user to obtain PDFs legitimately; do not bypass paywalls. **Deliverable:** `对标文献清单.csv`
(ranked, with metadata).

### 10. Verify hard submission requirements

From the journal's official Author Guidelines confirm, with access dates: word limit, abstract word
limit, title length/format, keyword count, figure/table count and format, reference style and count
limit, Graphical Abstract, Highlights, Cover Letter, declaration files (data availability, ethics, AI
use, conflict of interest, funding), and supplementary-material rules. Mark unconfirmable items
`需要人工核查`. **Deliverable:** `作者指南核查表.csv`.

### 11. Deep-learn the journal style on 8 dimensions

From the benchmark articles and the journal pages, learn: (1) title style, (2) abstract style, (3)
introduction style, (4) body structure and heading hierarchy, (5) figure/table style and density, (6)
reference style, density, and recency, (7) language style, (8) submission-file expectations. Then
compare the current draft item by item and list what must adapt (title, abstract, keywords, structure,
figures/tables, references, length, language, submission files). **Deliverable:**
`目标期刊适配学习报告.md` and `投稿格式适配清单.md`.

### 11b. Optional persistent prose-profile handoff (explicit request only)

Do not run this handoff during routine deep-learning. Run it only when the user explicitly asks to
generate, save, or reuse a target-journal 文风画像.

Prepare a bounded handoff from the already verified materials:

- `source_kind: journal-corpus` and the confirmed journal identity;
- absolute paths to `对标文献清单.csv` and `目标期刊适配学习报告.md`;
- the benchmark article source locators and access dates;
- intended profile scope and language;
- only abstracted prose-style observations supported across the corpus.

Do not create `prose-profiles/`, mutate style state, or install the project bootstrap here. Delegate
the handoff to `nature-prose-style`, which creates a draft, validates it, registers a usable profile,
and resolves the single-versus-multiple selection rule. If profile generation was not explicitly
requested, omit the handoff entirely and continue to step 12.

### 12. Report with evidence paths

Return the user-facing report from `core/output-contract.md` with the deliverable file paths first, so
the orchestrator can record them as `deep-learn` evidence. State plainly any journal facts still marked
`需要人工核查`. **Deliverable:** the final report and its listed file paths.
