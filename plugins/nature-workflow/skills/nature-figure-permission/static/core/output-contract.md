# Output contract

## Delivery format rule

- The **main deliverable is a Word `.docx`**. CSV and Markdown files are supporting working files
  only — never present them as the final delivery.
- Write the supporting files first, then package them into the `.docx`.
- Report the `.docx` **absolute path first**. That path is the evidence the orchestrator records
  with `complete --evidence <path>` for the `permission: 图片版权核查` step.

## Deliverable list

Write to the run's output directory (name files consistently within a run):

| File | Role |
|------|------|
| `figure-permission-deliverable.docx` | **Main deliverable / evidence** |
| `figure-permission-check.csv` | Supporting — per-item check table |
| `permission-request-info.csv` | Supporting — request information table |
| `permission-request-emails.md` | Supporting — filled email templates |
| `copyright-risk-list.md` | Supporting — risk-tier list |
| `caption-copyright-wording.md` | Supporting — caption/table-note wording suggestions |

### `.docx` main deliverable must contain

1. Overall permission-check summary (counts by permission status).
2. Per-item figure/table permission status.
3. Copyright-risk list with recommended actions.
4. Permission-request information (RightsLink / publisher systems / email).
5. Permission-request email templates.
6. Caption / table-note copyright wording suggestions.
7. Items requiring user action or manual verification (`需要人工核查`).
8. Handoff notes for the following submission-preparation steps.

## `figure-permission-check.csv` columns (minimum)

Figure/table number · title · item type · in-text citation position · whether original · whether
adapted · whether reproduced · source article title · source DOI · original figure/table number ·
source publisher · source license · whether permission is required · permission request method ·
current request status · caption copyright wording suggestion · risk tier · recommended action ·
whether manual check needed.

## `permission-request-info.csv` columns (minimum)

Request ID · figure/table number · permission platform or publisher · request link · source DOI ·
original figure/table number · use type (reuse / reproduce / adapt / modify / translate) · use
location (main text / graphical abstract / supplementary) · target manuscript title · target
journal · target publisher · whether open-access submission · whether commercial use · information
the user must fill in · current status · deadline reminder.

## Email templates (`permission-request-emails.md`)

```markdown
# 权限申请邮件模板

## 模板 1：申请复用原图（reproduce）

Subject: Permission request to reproduce Figure [X] from [Source Article Title]

Dear Permissions Team,

I am preparing a manuscript entitled "[Manuscript Title]" for submission to "[Target Journal]".
I would like to request permission to reproduce Figure [X] from the following article:

- Article title:
- Authors:
- Journal:
- Year:
- DOI:
- Publisher:

The figure will be used in [main text / graphical abstract / supplementary material] for scholarly
publication purposes. Proper attribution will be included according to your requirements.

Could you please let me know whether permission can be granted and what acknowledgement wording
should be used?

Sincerely,
[Author Name]

## 模板 2：申请改绘/改编原图（adapt）

Subject: Permission request to adapt Figure [X] from [Source Article Title]

Dear Permissions Team,

I am preparing a manuscript entitled "[Manuscript Title]" for submission to "[Target Journal]".
I would like to request permission to adapt Figure [X] from the following article:

- Article title:
- Authors:
- Journal:
- Year:
- DOI:
- Publisher:

The adapted figure will be redrawn and modified for use in [main text / graphical abstract /
supplementary material]. Proper attribution such as "Adapted from..." will be included according
to your requirements.

Could you please confirm whether permission is required and provide the required acknowledgement
wording?

Sincerely,
[Author Name]
```

## Risk-tier list (`copyright-risk-list.md`)

Four tiers. `高风险` / `中风险` / `低风险` collect: 图表编号 · 风险原因 · 来源 · 建议处理.
`需要人工核查` collects: 图表编号 · 不确定点 · 需要用户完成的操作.

## Caption wording suggestions (`caption-copyright-wording.md`)

Per item: 权限状态 · 建议图注/表注版权说明 · 是否需要等待授权后再定稿.

## User-facing report

Unless the user asks for another format, report in Chinese, `.docx` path first:

```markdown
## 图片版权核查结果

### 一、核查范围
- 正文图片 / 正文表格 / Graphical Abstract / TOC 图 / 补充图表 / 其他视觉素材数量

### 二、权限状态总览
- 原创/自绘，无需第三方授权：
- 综合绘制，建议标注参考文献：
- 改绘，需核查或申请授权：
- 复用，通常需要授权：
- 来源不清，需要人工核查：

### 三、高风险图表
- 图表编号 / 风险原因 / 建议处理

### 四、需要用户操作
- 需申请授权 / 需登录 RightsLink 或出版社系统 / 需补充来源信息 / 建议重绘或替换

### 五、输出文件
- Word 最终交付（evidence，绝对路径）：<figure-permission-deliverable.docx>
- 图片权限核查表 / 权限申请信息表 / 权限申请邮件模板 / 版权风险清单 / 图注版权标注建议
```
