# Output contract

## Full package

The **main deliverable is a Word `.docx` file**, `投稿指导交付文件.docx`. Markdown files are
supporting working files, not the final delivery. A complete job produces, under the step's output
directory:

- `投稿指导交付文件.docx` — the final main deliverable and the **evidence file** for the
  orchestrator;
- `投稿材料清单.md` — submission material checklist;
- `投稿步骤指导.md` — step-by-step submission guide (upload order + walkthrough);
- `投稿系统字段填写建议.md` — submission-system field suggestions;
- `缺失材料与风险清单.md` — missing-material and risk list;
- `最终提交前确认清单.md` — pre-submit confirmation checklist;
- `投稿后记录.md` — post-submission record template.

The `.docx` must consolidate: target journal and submission-system entry info; the final material
checklist; recommended filenames and upload order; submission-system field suggestions; the
missing-material and risk list; the pre-submit confirmation checklist; user-only-operation reminders
(login, captcha, payment, copyright transfer, legal declarations, final Submit); and the
post-submission record template.

## Submission material checklist fields

Record each material with: file name; file type; corresponding submission-system field; whether
required; current status; format requirement; whether user confirmation is needed; risk note.

| 序号 | 材料 | 是否必需 | 当前状态 | 建议文件名 | 上传栏目 | 需用户确认 | 风险提示 |
|---:|---|---|---|---|---|---|---|
| 1 | Main Manuscript | 是 |  |  |  |  |  |
| 2 | Title Page | 按期刊要求 |  |  |  |  |  |
| 3 | Cover Letter | 按期刊要求 |  |  |  |  |  |
| 4 | Figures |  |  |  |  |  |  |
| 5 | Tables |  |  |  |  |  |  |
| 6 | Graphical Abstract | 按期刊要求 |  |  |  |  |  |
| 7 | Highlights | 按期刊要求 |  |  |  |  |  |
| 8 | Supplementary Materials |  |  |  |  |  |  |
| 9 | Declarations / Conflict of Interest | 是 |  |  |  |  |  |
| 10 | Funding Statement | 是 |  |  |  |  |  |
| 11 | Data Availability Statement | 按期刊要求 |  |  |  |  |  |
| 12 | AI Use Statement | 按期刊要求 |  |  |  |  |  |
| 13 | Figure Permission Documents | 按需 |  |  |  |  |  |
| 14 | Suggested / Opposed Reviewers | 按期刊要求 |  |  |  |  |  |

## Filename conventions

Filenames must be clear, English, and free of spaces or problematic special characters
(`/ \ : * ? " < > |`), and compatible with the submission system. Recommended examples:

- `Manuscript_[ShortTitle].docx`
- `Title_Page_[ShortTitle].docx`
- `Cover_Letter_[Journal].docx`
- `Figure_1.tif`, `Figure_2.tif`
- `Table_1.docx`
- `Graphical_Abstract.tif`
- `Highlights.docx`
- `Supplementary_Material.docx`
- `Declaration_Statement.docx`
- `Figure_Permissions.pdf`

## Pre-submit confirmation checklist

Emit this as checkboxes for the author to confirm personally:

```markdown
- [ ] 主文稿为最终版本。
- [ ] Title Page / Cover Letter 为最终版本。
- [ ] 所有图表文件已命名并按顺序上传，编号正确。
- [ ] Graphical Abstract / Highlights（若期刊要求）已准备。
- [ ] 所有补充材料已上传。
- [ ] 声明信息（利益冲突、基金、数据可用性、AI 使用）已确认。
- [ ] 图片版权和授权状态已确认，无未解决的版权风险。
- [ ] 作者顺序、单位、通讯作者和 ORCID 信息已确认。
- [ ] 推荐审稿人 / 排除审稿人信息已确认（若期刊要求）。
- [ ] APC / 开放获取 / 许可协议选项已确认（由用户本人完成付款与签署）。
- [ ] 最终 Submit 前，用户已人工逐页检查全部投稿信息。
```

## Post-submission record template

```markdown
# 投稿后记录
- 目标期刊：
- 投稿系统：
- Manuscript ID：
- 提交日期：
- 当前状态：
- 需跟进事项：
```

## Delivery note

State plainly that the package is a **submission aid**, not a submitted manuscript: account login,
captcha, authentication, payment, copyright transfer, legal declarations, and the final Submit are
completed by the author. Do not describe the package as "submitted" or "ready to submit" merely
because the checklist is filled. Anything unverifiable stays marked `需要人工核查`.
