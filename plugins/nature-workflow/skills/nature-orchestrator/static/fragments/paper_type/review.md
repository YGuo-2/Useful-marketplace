# Genre template — review (综述)

The ordered task sequence for a literature review, from topic to submission. This
is the data the orchestrator seeds into the state engine and then walks. Delegate
each step to its owner; never re-implement an owner skill here.

## Task sequence (14 steps)

Order follows each owner skill's declared upstream dependency (and SCI's original
03→04→05→06): search exports records → topic reads those records → benchmark builds
the classification framework → screen classifies against that framework.

| # | task `id: title` | Owner (delegate) | Evidence a completed step records | Fork | Review-specific |
|---|---|---|---|---|---|
| 1 | `search: 检索式生成与多源检索` | **nature-academic-search** | search strings + exported `.ris/.nbib` path | | generic |
| 2 | `topic: 选题与研究空白识别` | **nature-topic** | topic-decision doc: 3 candidates + chosen + rationale | ✔ | mostly generic |
| 3 | `benchmark: 对标综述库建立与学习` | **nature-benchmark** | benchmark-corpus report + classification guide | | **yes** |
| 4 | `screen: 文献筛选与分类` | **nature-screening** | screened library table (top-500 strongly-relevant, 2/3-level classes) | | **yes (top-500)** |
| 5 | `read: 文献精读` | **nature-reader** | reading notes path | | generic |
| 6 | `outline: 综述框架搭建` | **nature-writing** (review type) | review outline / paragraph map | ✔ | **yes** |
| 7 | `draft: 分章撰写` | **nature-writing** (review type) | section drafts path | | **yes** |
| 8 | `figure: 图表制作与排版` | **nature-figure** | figure files + caption/reference plan | | generic |
| 9 | `journal: 目标期刊选择与深度学习` | **nature-journal** | journal shortlist + fit/risk report + style-learning notes | ✔ | generic |
| 10 | `polish: 深度润色` | **nature-polishing** | polished manuscript path | | generic |
| 11 | `permission: 图片版权核查` | **nature-figure-permission** | figure-permission checklist + risk table | | generic |
| 12 | `coverletter: Cover Letter 撰写` | **nature-cover-letter** | cover letter `.docx` + declaration checklist | | generic |
| 13 | `submit: 投稿指导` | **nature-submission** | submission material list + pre-submit checklist | | generic |
| 14 | `response: 审稿意见回复` | **nature-response** | point-by-point response path | | generic |

**Owner status.** Every step delegates to a skill that exists in this plugin today.
Steps 2/3/4/9/11/12/13 (topic, benchmark, screen, journal, permission, coverletter,
submit) were fused in from SCI从0-1workflow; the rest reuse existing nature-* skills.
Always `complete` each step with an `evidence` path — even a manually driven step —
so the flow stays traceable and resumable.

**Domain parameters to pass as the step brief** (do not inline the owner's logic):
- Step 3 `benchmark`: pick ~10 best-matching high-quality reviews; **learn
  structure/narrative/figure strategy only, never copy** titles/sections/prose. It
  emits the classification framework that step 4 consumes.
- Step 4 `screen`: keep the top-500 strongly-relevant only; never pad with weak
  matches; conservative dedup (DOI/PMID first); build 2/3-level classes from step
  3's framework.
- Steps 6–7 `outline`/`draft`: organize by argument, not paper-by-paper; this is
  `nature-writing`'s `review` paper_type.
- Steps 9/11/12/13: dynamic facts (IF/quartile/APC/scope, license status,
  submission rules) must be verified live by the owner; unverifiable items are
  marked `需要人工核查`.

## Seed command

Run once from the repository root (or the `nature_new_workflow` MCP equivalent with
`tasks` = these strings in order):

```bash
python plugins/nature-workflow/scripts/nature_progress.py new \
  --slug review-<short-topic> --title "<review title or topic>" \
  --genre review \
  --task "search: 检索式生成与多源检索" \
  --task "topic: 选题与研究空白识别" \
  --task "benchmark: 对标综述库建立与学习" \
  --task "screen: 文献筛选与分类" \
  --task "read: 文献精读" \
  --task "outline: 综述框架搭建" \
  --task "draft: 分章撰写" \
  --task "figure: 图表制作与排版" \
  --task "journal: 目标期刊选择与深度学习" \
  --task "polish: 深度润色" \
  --task "permission: 图片版权核查" \
  --task "coverletter: Cover Letter 撰写" \
  --task "submit: 投稿指导" \
  --task "response: 审稿意见回复"
```

Steps 2, 6, 9 are decision forks — apply `core/decision.md` before advancing.

## Optional delegates (inject with add-task)

Not seeded by default; insert on demand with `add-task` (its output feeds no later
step, so it stays out of the fixed sequence). The delegate is documented here so the
orchestrator inserts from the template, not from memory.

| task `id: title` | Owner (delegate) | Evidence | When |
|---|---|---|---|
| `reviewer: 投稿前预审` | **nature-reviewer** | reviewer report path (3 reports + cross-review synthesis) | pre-submission self-review, after the manuscript is polished |

```bash
# after step 10 polish, before the submission-packaging tail
python plugins/nature-workflow/scripts/nature_progress.py add-task "reviewer: 投稿前预审" --after polish
```
