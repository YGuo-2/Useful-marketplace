# Genre template — research (原始研究)

The ordered task sequence for an original research article reporting the author's
own primary observation or experiment, from topic to submission. This is the data
the orchestrator seeds into the state engine and then walks. Delegate each step to
its owner; never re-implement an owner skill here.

## Task sequence (15 steps)

Order follows the author's own data flow: search exports records → topic frames the
gap → read builds understanding of prior work → outline fixes the IMRaD skeleton →
methods and results report the author's primary data → data packages every dataset
for availability → draft adds introduction/discussion and integrates the whole →
figure/journal/polish and the submission tail. Unlike `review`, there is no
benchmark-corpus / top-500 screening stage: an original study synthesizes its own
results, not the literature.

| # | task `id: title` | Owner (delegate) | Evidence a completed step records | Fork | Research-specific |
|---|---|---|---|---|---|
| 1 | `search: 检索式生成与多源检索` | **nature-academic-search** | search strings + exported `.ris/.nbib` path | | generic |
| 2 | `topic: 选题与研究空白识别` | **nature-topic** | topic-decision doc: 3 candidates + chosen + rationale | ✔ | generic |
| 3 | `read: 文献精读` | **nature-reader** | reading notes path | | generic |
| 4 | `outline: IMRaD 框架搭建` | **nature-writing** (research type) | IMRaD outline / section map | ✔ | **yes** |
| 5 | `methods: 方法与实验部分撰写` | **nature-writing** (research type) | methods draft path (reproducible protocol) | | **yes** |
| 6 | `results: 结果部分撰写` | **nature-writing** (research type) | results draft + figure/table inventory | | **yes** |
| 7 | `data: 数据可用性声明与仓库/FAIR 规划` | **nature-data** | data-availability statement + repository/accession plan + FAIR checklist | | **yes** |
| 8 | `draft: 引言与讨论撰写、全文整合` | **nature-writing** (research type) | full-manuscript draft path | | **yes** |
| 9 | `figure: 图表制作与排版` | **nature-figure** | figure files + caption/reference plan | | generic |
| 10 | `journal: 目标期刊选择与深度学习` | **nature-journal** | journal shortlist + fit/risk report + style-learning notes | ✔ | generic |
| 11 | `polish: 深度润色` | **nature-polishing** (research type) | polished manuscript path | | generic |
| 12 | `permission: 图片版权核查` | **nature-figure-permission** | figure-permission checklist + risk table | | generic |
| 13 | `coverletter: Cover Letter 撰写` | **nature-cover-letter** | cover letter `.docx` + declaration checklist | | generic |
| 14 | `submit: 投稿指导` | **nature-submission** | submission material list + pre-submit checklist | | generic |
| 15 | `response: 审稿意见回复` | **nature-response** | point-by-point response path | | generic |

**Owner status.** Every step delegates to a skill that exists in this plugin today.
`nature-writing` and `nature-polishing` drive their **`research`** paper_type for the
outline/methods/results/draft/polish steps; `nature-data` owns the data-availability
step. Always `complete` each step with an `evidence` path — even a manually driven
step — so the flow stays traceable and resumable.

**Domain parameters to pass as the step brief** (do not inline the owner's logic):
- Steps 4–6/8 `outline`/`methods`/`results`/`draft`: this is `nature-writing`'s
  `research` paper_type (IMRaD). Methods must be reproducible; results state findings
  without interpreting them (interpretation belongs in the discussion drafted at step
  8). Report the author's own primary data — never fabricate observations.
- Step 7 `data`: `nature-data` owns the data-availability statement, repository/
  accession plan, dataset citations, and FAIR metadata. **Never invent DOIs or
  accession numbers**; "available upon request" is flagged as weak; map every dataset
  to a concrete access route.
- Steps 10/12/13/14: dynamic facts (IF/quartile/APC/scope, license status, submission
  rules) must be verified live by the owner; unverifiable items are marked `需要人工核查`.

## Seed command

Run once from the repository root (or the `nature_new_workflow` MCP equivalent with
`tasks` = these strings in order, and `genre` = `research`):

```bash
python plugins/nature-workflow/scripts/nature_progress.py new \
  --slug research-<short-topic> --title "<paper title or topic>" \
  --genre research \
  --task "search: 检索式生成与多源检索" \
  --task "topic: 选题与研究空白识别" \
  --task "read: 文献精读" \
  --task "outline: IMRaD 框架搭建" \
  --task "methods: 方法与实验部分撰写" \
  --task "results: 结果部分撰写" \
  --task "data: 数据可用性声明与仓库/FAIR 规划" \
  --task "draft: 引言与讨论撰写、全文整合" \
  --task "figure: 图表制作与排版" \
  --task "journal: 目标期刊选择与深度学习" \
  --task "polish: 深度润色" \
  --task "permission: 图片版权核查" \
  --task "coverletter: Cover Letter 撰写" \
  --task "submit: 投稿指导" \
  --task "response: 审稿意见回复"
```

Steps 2, 4, 10 are decision forks — apply `core/decision.md` before advancing.

## Optional delegates (inject with add-task)

Not seeded by default; insert on demand with `add-task`. These delegates stay out of
the fixed genre sequence because they require an explicit user request. The delegate
is documented here so the orchestrator inserts from the template, not from memory.

| task `id: title` | Owner (delegate) | Evidence | When |
|---|---|---|---|
| `prose-style: 文风画像生成与注册` | **nature-prose-style** | validated `ready`/`calibrated` profile path + registration result | only after an explicit request for a persistent profile; before the next writing/polishing task |
| `reviewer: 投稿前预审` | **nature-reviewer** | reviewer report path (3 reports + cross-review synthesis) | pre-submission self-review, after the manuscript is polished |

```bash
# recommended before the first prose-producing step; never add by default
python plugins/nature-workflow/scripts/nature_progress.py add-task "prose-style: 文风画像生成与注册" --after read

# after step 11 polish, before the submission-packaging tail
python plugins/nature-workflow/scripts/nature_progress.py add-task "reviewer: 投稿前预审" --after polish
```

Registering one usable profile immediately selects it as `auto_single`. Registering two or more
requires an exact user choice before any downstream prose task continues. The profile task's evidence
does not replace the audit receipt required for each later guarded prose output.
