# business-bid-outline

本仓库维护商务标流程相关的本地 Agent Skill。当前包含两个相互独立的能力：

- `.claude/skills/business-bid-outline`：根据历史商务标投标文件和当前招标文件生成 `business_bid_outline.v1` 的 `outline.json`。
- `.claude/skills/bid-business-format-cleaner`：读取已成稿商务标 `.docx` 和 S2 审核后的 `outline.json`，清洗 Word 格式并输出新的 `.docx`。

两个 skill 都只面向商务标流程，不接入 `bid-project-mvp` 后端，也不修改技术标流程。

## 商务标目录生成

`business-bid-outline` 用于生成 `outline.json`。它会优先学习历史商务标投标文件的目录结构、层级、顺序和编号样式，再结合当前招标文件匹配 `source_text` 与必要性。

常用辅助脚本位于：

```powershell
.\.claude\skills\business-bid-outline\scripts
```

输出的 `outline.json` 应使用 `schema_version: business_bid_outline.v1`，并在 `sections` 及各级 `children` 中保留 `id`、`title`、`number`、`level` 等字段，供后续 Word 格式清洗使用。

## 商务标 Word 格式清洗

`bid-business-format-cleaner` 只处理一份已经成稿的商务标 `.docx`。它不会覆盖输入文件，只会写入 manifest 中指定的 `outputFile`。

主要能力：

- 按 `outline.json` 顺序匹配 Word 段落，优先匹配 `number + title`，再匹配纯 `title`。
- 将匹配段落提升为 `Heading {level}`，标题文本规范为 `{number} {title}` 或 `title`。
- 清理标题段落残留自动编号，改用文本编号。
- 统一正文、表格、页眉和自动目录格式。
- 插入或刷新 TOC 域，并设置 `updateFields=true`。
- 清理多余空白页，并在有正文的小节结束后补齐分页符。
- 生成 `business_format_clean_report.md`，记录匹配数量、未匹配标题、TOC、页眉和格式风险。

### 依赖

建议使用 Python 3.10+：

```powershell
python -m pip install python-docx lxml
```

### Manifest 字段

```json
{
  "inputFile": "待清洗商务标.docx",
  "outlineFile": "outline.json",
  "outputFile": "清洗后商务标.docx",
  "projectName": "项目名称",
  "styleSpecPath": "references/business_heading_style.json"
}
```

字段说明：

- `inputFile`：待清洗商务标 `.docx`。
- `outlineFile`：S2 审核后的 `business_bid_outline.v1` 文件。
- `outputFile`：清洗后 `.docx` 输出路径，必须不同于 `inputFile`。
- `projectName`：用于页眉，模板为 `{projectName}投标文件-商务部分`。
- `styleSpecPath`：可选，默认读取 skill 内的 `references/business_heading_style.json`。

所有页面、标题、正文、表格、页眉和目录格式值都放在 `references` 下：

- `references/business_heading_style.json`
- `references/business_toc_style.json`
- `references/business_style_spec.md`

### 最小示例

仓库内置了可直接运行的最小示例：

```powershell
cd .\.claude\skills\bid-business-format-cleaner
python .\scripts\run_from_manifest.py .\examples\minimal_manifest.json --response summary
```

运行后会生成：

- `examples/out/minimal_business_bid.cleaned.docx`
- `examples/out/business_format_clean_report.md`

实际项目使用时，复制 `examples/minimal_manifest.json` 并替换为真实的 `inputFile`、`outlineFile`、`outputFile` 和 `projectName`。

### 返回 JSON

使用 `--response summary` 时返回：

```json
{
  "schema_version": "bid-business-format-clean-v1",
  "inputFile": "...",
  "outlineFile": "...",
  "outputFile": "...",
  "reportFile": "...",
  "summary": {
    "outlineCount": 0,
    "matchedHeadingCount": 0,
    "unmatchedHeadingCount": 0,
    "tocInserted": true,
    "tocPresent": true,
    "headerCleaned": true,
    "insertedPageBreaks": 0,
    "removedBlankPageBreaks": 0,
    "riskCount": 0
  }
}
```

## 验证命令

在格式清洗 skill 目录运行：

```powershell
cd .\.claude\skills\bid-business-format-cleaner
python -m unittest discover -s .\tests
python -m py_compile .\scripts\run_from_manifest.py .\scripts\outline_matcher.py .\scripts\clean_docx.py .\scripts\verify.py .\scripts\pagination_cleaner.py
```

## 产物约定

不要提交业务输入文档、清洗后输出文档、运行报告或临时 docx。仓库 `.gitignore` 已忽略常见运行产物。
