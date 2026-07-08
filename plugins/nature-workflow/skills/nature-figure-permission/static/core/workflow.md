# Workflow

Run these steps in order. Each step names the product it records. The final product is the
`.docx` deliverable described in `output-contract.md`; its absolute path is the evidence the
orchestrator records for the `permission: 图片版权核查` step.

## Accepted inputs

The polished manuscript; the figure/table layout and in-text citation plan; the finished
figure/table list; per-item source notes (original / self-drawn / adapted / cited / reproduced /
screenshot / software- or database-generated); and the target journal name, publisher, author
guidelines, and figure/permission policy.

If per-item source notes are missing for an item, ask the user to supply them or mark that item
`来源不清，必须人工核查`. Do not infer a source.

## 1. Build the visual inventory

List every visual item with a stable ID: main-text figures, main-text tables, Graphical Abstract,
TOC figure, supplementary figures, supplementary tables, and any other visual (schematic,
flowchart, map, screenshot, clinical image). Record for each: number, title, purpose, and in-text
citation position.

**Product:** a complete item inventory (feeds the check table).

## 2. Classify every item

Assign exactly one of the eight types:

| # | Type | What it means | Default permission posture |
|---|------|---------------|----------------------------|
| 1 | Original figure | Fully author-created; does not reuse another figure's layout or specific visual expression | Usually no third-party permission, but still record as original and check for embedded third-party content |
| 2 | Self-drawn mechanism figure / flowchart | Synthesized from multiple references; does not reuse one source's concrete graphic structure | Usually original/synthesized; cite supporting references in the caption |
| 3 | Adapted figure | Based on the graphic structure, pathway, framework, or layout of one or more sources, even if redrawn | May need `Adapted from…`; permission depends on source copyright, degree of adaptation, and publisher rules |
| 4 | Reproduced figure | Directly or near-directly uses the original figure | Usually requires permission unless the license explicitly allows reuse and the target journal accepts it |
| 5 | Partially reused figure | Uses a panel, local element, structure, or image from the original | Requires careful permission review |
| 6 | Reused / adapted table | Copies or adapts the original table's structure or content | Determine whether it is an adapted table or a reproduced table |
| 7 | Screenshot / website image | From a database, software, webpage, clinical image, product doc, or map | Check source terms plus privacy/ethics risk |
| 8 | AI-generated image | Record the tool, use case, and target-journal AI-image policy | Must not fabricate research/experimental/clinical/microscopy images |

**Product:** each item tagged with a type (feeds the check table).

## 3. Collect source facts for every non-original item

For any item that is not fully original, record: source article title, authors, journal,
publisher, year, DOI, original figure/table number, original figure/table link, copyright
statement, and license type. Any field you cannot verify is left blank and the item is flagged
`需要人工核查` — do not fabricate a DOI, author, journal, or license.

**Product:** a source-fact record per non-original item.

## 4. Apply the permission-judgment rules

Verify the relevant policies online first (see `stance.md`), then apply:

1. **Fully original figure** → `原创，通常无需第三方授权`. Still check for embedded third-party
   logos, maps, clinical images, or database screenshots.
2. **Synthesized from multiple references** → `综合绘制`; suggest citing supporting references in
   the caption.
3. **Clearly adapted from a single source** → `改绘，需核查是否需要授权`; suggest `Adapted from…`,
   but the final wording follows the permission requirement.
4. **Directly reproduced figure or table** → `复用，通常需要授权`.
5. **Figure from an open-access article** → always verify the exact license. CC BY often allows
   reuse with attribution, but target-journal requirements still apply; CC BY-NC, CC BY-NC-ND, and
   custom publisher licenses require careful review.
6. **Figure without license information** → do not assume reusable; mark `需要人工核查`.
7. **Target journal has stricter figure/table permission rules** → follow the stricter of the
   source-publisher and target-journal requirements.

**Product:** a permission judgment per item.

## 5. Set permission status and copyright risk tier

Assign one permission status per item: permission not required · source acknowledgement required
(no separate permission) · permission required, not yet requested · requested, awaiting response ·
permission granted · permission denied or fee/conditions unacceptable · source unclear, manual
check required.

Assign one risk tier: `高风险` · `中风险` · `低风险` · `需要人工核查` (see `output-contract.md`
for what each tier collects).

**Product:** status + risk tier per item (feeds the check table and the risk list).

## 6. Prepare request materials for items needing permission

For each item requiring permission, gather: target journal, target manuscript title, author
placeholder, purpose of use, use type (reprint / reproduce / adapt / modify / translate / reuse in
review article), use scope (online / print / open access / supplementary), original figure/table
info, target figure/table info, and whether commercial use applies. Where RightsLink / Copyright
Clearance Center / a publisher system is needed, produce a field-by-field request information
table; where an email request is suitable, fill in the email templates from `output-contract.md`.

**Product:** the request information table and the filled email templates.

## 7. Recommend an action for every risk item

For risk items, recommend one of: request permission · redraw as original · delete or replace ·
convert to a text description · use an open-license alternative source.

**Product:** a recommended action per risk item.

## 8. Assemble the deliverable

Produce the supporting CSV/Markdown working files and then the `.docx` main deliverable, following
`output-contract.md`. Report the `.docx` absolute path first as the step evidence.

**Product:** the `.docx` deliverable (evidence) plus its supporting files.
