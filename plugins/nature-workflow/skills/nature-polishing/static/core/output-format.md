# Output format

Default output:

1. The polished text as plain prose, not in a code block.
2. `Revision notes:` with `3-5` short bullets on the major structural and stylistic changes.
3. If the rewrite changed section logic, say so explicitly.
4. `Style receipt:` — only when `nature_style_resolve` returned `resolved`; give the selected profile ID and tool-created receipt path. Omit this field for `not_configured`, `not_applicable`, and layout-only work.

If the user asks for side-by-side revision, provide:

- `Original`
- `Polished`
- `Why changed`

If any paragraph's structural problem could not be fixed without inventing content, say so under `Revision notes:` instead of papering over it.

For resolved-profile workflow work, the displayed polished prose must be the same bytes written to the audited evidence file. Do not audit an intermediate version and then make unrecorded edits.
