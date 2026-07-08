# Workflow and per-step products

## Accepted inputs

The skill may receive: the final (deep-polished) manuscript; Title Page; Cover Letter; figure
files; table files; Graphical Abstract; Highlights; supplementary materials; declaration /
conflict-of-interest / funding / data-availability / AI-use statements; figure-permission records
and copyright-risk notes; author-guideline check tables; the target journal name, submission-system
link, publisher, and article type; author, affiliation, corresponding-author, and ORCID details.

If a required upstream material (final manuscript, cover letter, or figure-permission check) is
missing, say so and route the user back to the owning step instead of fabricating it.

## Workflow

Run these steps in order. Each step names the product it must leave behind.

1. **Intake and readiness.** List which materials are present, which are missing, and the detected
   target journal, submission system, and article type.
   *Product:* a one-line materials-and-target summary.
2. **Verify guidelines online.** Verify the target journal's current submission system and author
   guidelines; record the access date; mark unverifiable items `需要人工核查`.
   *Product:* a short verified-requirements note with source URLs and access date.
3. **Build the submission material checklist.** Cover every material in `core/stance.md` and give
   each a status (`complete` / `needs format adjustment` / `needs user confirmation` / `missing` /
   `not applicable`), required-or-not, submission-system field, format requirement, and risk note.
   *Product:* `投稿材料清单.md`.
4. **Plan file naming.** Assign clear, English, submission-system-safe filenames (no problematic
   special characters), using the examples in `core/output-contract.md`.
   *Product:* the recommended-filename column filled in the material checklist.
5. **Plan upload order.** Define the order in which files are uploaded and the field each maps to.
   *Product:* the upload-order section of `投稿步骤指导.md`.
6. **Draft submission-system field suggestions.** Prepare Title, Running Title, Abstract, Keywords,
   Article Type, corresponding author, co-authors, affiliations, ORCID, funding, conflict of
   interest, data availability, AI use, suggested/opposed reviewers, cover-letter field, and
   comments-to-editor. Flag any field that needs user confirmation.
   *Product:* `投稿系统字段填写建议.md`.
7. **Missing-material and risk check.** Identify must-fix gaps and pre-submission risks: missing
   author confirmation, missing declarations, unresolved figure permissions, format mismatches,
   word/abstract/figure-count limits exceeded, reference style not adapted, APC/OA not confirmed,
   suggested-reviewer info missing.
   *Product:* `缺失材料与风险清单.md`.
8. **Step-by-step submission guide.** Write the ordered submission-system walkthrough (entry,
   create submission, fill manuscript info, upload files, reviewers, final check, post-submission
   record), honoring the security red lines in `core/stance.md`.
   *Product:* the body of `投稿步骤指导.md`.
9. **Pre-submit confirmation checklist.** Produce the checkbox list from `core/output-contract.md`
   for the author to confirm personally before Submit.
   *Product:* `最终提交前确认清单.md`.
10. **Assemble the deliverable.** Consolidate the checklist, filenames, upload order, field
    suggestions, risk list, pre-submit checklist, user-only-operation reminders, and a
    post-submission record template into the Word `.docx` main deliverable.
    *Product:* `投稿指导交付文件.docx` (the evidence file) plus the supporting Markdown files.

## Handoff to the orchestrator

This step is delegated by `nature-orchestrator`. When done, report the **absolute path** of
`投稿指导交付文件.docx` as the evidence file so the orchestrator can `complete --evidence <that
path>`. If the deliverable could not be assembled (blocking missing material or unverifiable
requirements), report the blocker instead of a false completion.
