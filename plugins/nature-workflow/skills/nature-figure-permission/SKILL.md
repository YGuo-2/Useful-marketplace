---
name: nature-figure-permission
description: >-
  Check the copyright and permission status of every figure, table, and visual item in a
  manuscript before submission, then prepare the permission-request materials. Use when the user
  asks to audit figure/table copyright, decide whether an image is original / adapted / reproduced /
  reused, whether an "Adapted from" or "Reproduced with permission" caption is needed, whether a
  figure from an open-access article (CC BY / CC BY-NC / CC BY-NC-ND) may be reused, how to request
  permission via RightsLink or Copyright Clearance Center, how to write a permission-request email,
  or to grade copyright risk for figures, tables, adapted/redrawn figures, reproduced figures,
  screenshots, maps, clinical images, schematics, flowcharts, Graphical Abstract, TOC figures, and
  supplementary visuals. Also trigger on Chinese phrasings even without the word "Nature":
  图片版权核查、图表授权、版权状态核查、改绘图授权、复用图授权、图片权限申请、授权邮件、
  RightsLink 申请、CC BY 许可核查、Graphical Abstract 版权、补充图表版权、版权风险、图注版权标注、需要人工核查.
metadata:
  version: 0.1.0
  status: Beta
  author: Fused from SCI 17-SCI图片引用权限申请器, refactored into static/dynamic layers
---

# Nature Figure Permission — Router

This skill is an **atomic step delegated by `nature-orchestrator`** (review flow step
`permission: 图片版权核查`). The orchestrator `start`s the step, you run the domain logic
below, and you hand back an evidence file path so it can `complete --evidence <path>`.

It is split into two layers:

- A **static layer** under `static/` that carries all the domain logic (stance and red lines,
  the classification/judgment workflow, and the deliverable contract).
- A **dynamic layer** (this file plus `manifest.yaml`) that loads the core every time.

Do not apply the permission logic from memory or from this router, and do not judge any
publisher policy or license status from memory. Always load the fragments from disk, and verify
dynamic facts (journal figure policy, license terms, permission requirements) live.

## Routing protocol

1. **Load the manifest and the core layer.** Read [manifest.yaml](manifest.yaml), then read every
   file under `always_load`:
   - `../_shared/core/ethics.md` — the citation/AI/image ethics red lines shared across nature-* skills.
   - `static/core/stance.md` — what this step produces, the default stance, the Prohibited Actions
     safety red lines, mandatory online verification, and the source hierarchy.
   - `static/core/workflow.md` — the ordered steps, the eight figure/table types, and the
     permission-judgment rules, with the product each step records.
   - `static/core/output-contract.md` — the deliverable list, the `.docx` main-deliverable rule,
     CSV/Markdown supporting-file schemas, email templates, risk tiers, and caption wording.

2. **Run the workflow** in `static/core/workflow.md`: build the full visual inventory, classify
   every item, collect source facts for non-original items, apply the permission-judgment rules,
   set permission status and risk tier, prepare request materials and emails, and assemble the
   deliverable. Mark anything unverifiable as `需要人工核查`; never assume permission is unnecessary.

3. **Assemble and report the deliverable** per `static/core/output-contract.md`. The main
   deliverable is a Word `.docx`; CSV/Markdown files are supporting working files only. Report the
   absolute path of the `.docx` first — that path is the evidence the orchestrator records.
