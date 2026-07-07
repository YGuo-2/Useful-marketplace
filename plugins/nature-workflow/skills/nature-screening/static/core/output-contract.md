# Output contract

All deliverables are tables and lists (`.csv`, `.ris`, `.md`). There is no `.docx` output. Write
every derived file under the output directory (default `nature-screening-output/`); keep the raw
export files outside it and byte-for-byte unchanged.

## Deliverable file tree

Create these when feasible:

```text
nature-screening-output/
├── 输入/
│   └── 上游输入文件清单.md
├── 输出/
│   ├── XXXXX综述文献库/
│   │   ├── XXXXX综述文献库总表.csv
│   │   ├── XXXXX综述文献库.ris
│   │   ├── 二级三级分类表.csv
│   │   ├── Zotero导入映射表.csv
│   │   ├── Zotero集合结构清单.md
│   │   └── 分类后RIS文件清单.csv
│   ├── Zotero导入文件/
│   │   └── XXXXX综述文献库/
│   │       ├── 01-背景与概念基础/
│   │       ├── 02-核心理论-机制-原理/
│   │       ├── 03-关键方法-技术-模型/
│   │       ├── 04-对象-系统-场景-证据/
│   │       ├── 05-指标-表征-评价体系/
│   │       ├── 06-设计-优化-干预-解决策略/
│   │       ├── 07-转化-工程实现-应用/
│   │       ├── 08-争议-局限-研究空白/
│   │       ├── 09-方法学-平台-数据与工具/
│   │       ├── 10-综述与指南背景文献/
│   │       └── 99-待人工核查/
│   ├── 筛选结果总表.csv
│   ├── 相关性排序表.csv
│   ├── 强相关前500文献.csv
│   ├── 纳入文献列表.csv
│   ├── 排除文献列表.csv
│   ├── 重复文献记录.csv
│   └── 待人工核查文献.csv
├── 过程记录/
│   ├── 文献筛选日志.md
│   ├── 去重报告.md
│   └── 分类日志.md
└── 质量核查/
    ├── 筛选分类质量核查.md
    └── Zotero导入准备核查.md
```

The `Zotero导入映射表.csv` should carry at least: record ID, DOI, title, year, journal, second-level
category, third-level category, target collection path, recommended import reference file, primary/
secondary classification, and manual-check reason. Folder-name variants use `-` where a category
label contains `/`, because `/` is not filename-safe.

## Evidence file

When `nature-orchestrator` completes this step, the natural `--evidence` path is
`输出/XXXXX综述文献库/二级三级分类表.csv` (the classified library) or `输出/纳入文献列表.csv`
(the retained set). Always report absolute paths.

## User-facing report format

Report in Chinese. Unless the user asks for another format, return:

```markdown
## 文献筛选分类结果

- 原始记录数：
- 去重后记录数：
- 强相关文献数：
- 最终纳入“XXXXX综述文献库”数量：
- 排除文献数：
- 待人工核查文献数：

## 筛选分类边界

- 已确认综述主题：
- 学科与研究方向：
- 使用的题名/摘要匹配标准：
- 从泛到精的收敛依据：
- 前 N 保留规则（默认 500）：
- 不纳入或待核查的主要原因：

## XXXXX综述文献库分类结构

| 二级分类 | 三级分类数量 | 文献数量 | 说明 |
|---|---:|---:|---|

## 导入准备

- 顶层集合建议：
- 二级/三级集合结构：
- 分类后 RIS/参考文献文件：
- 导入映射表：
- 需要人工确认的位置：

## 生成文件

- 筛选结果总表：
- 相关性排序表：
- 强相关前500文献：
- XXXXX综述文献库：
- 二级三级分类表：
- 导入映射表：
- 排除文献列表：
- 待人工核查文献：
```

Lead with any blocking issue (missing inputs, unverifiable metadata, discipline mismatch) before the
result tables. State the retention target actually used and the actual retained count when it is
below target.
