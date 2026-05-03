---
name: business-bid-outline
description: 当用户要求生成商务标目录、商务标大纲、商务响应目录、投标文件目录结构或 outline.json 时使用。先学习历史商务标投标文件目录结构，再用当前招标文件要求匹配 source_text 并补强特殊提交材料，最终只输出 outline.json。
---

# Business Bid Outline

你是资深标书专家。你的任务是生成商务标目录结构文件 `outline.json`：先学习历史商务标投标文件的目录结构、层级和顺序，再用当前招标文件中的特殊条款、约定、必须承诺项、必须提交材料、废标/资格/符合性/商务评分要求补强目录。

## 触发场景

当用户要求生成以下内容时，必须使用本 skill：

- 商务标目录
- 商务标大纲
- 商务响应目录
- 投标文件目录结构
- `outline.json`

## V1 边界

V1 只做目录结构判断，最终只输出一个 `outline.json`。

**执行前准备：**
用户需在执行本 skill 前编辑 `user_confirmed_inputs.json`，填入响应标段、投标人类型等关键上下文。AI 将直接读取，不再逐一询问；若某信息无法由招标文件替用户决定且 JSON 中未填，写入 `review_items`。

禁止：

- 生成商务标正文
- 生成 Markdown 目录
- 自动生成完整投标文件
- 输出 `outline.json` 以外的最终交付物
- 把当前招标文件中的“投标文件格式”“响应文件格式”等不稳定目录块作为顶层 `sections` 的主来源
- 无条件把历史投标文件原文作为最终 `source_text`

## 工作原则

- 历史商务标投标文件是目录结构学习来源：用于学习顶层顺序、层级关系、常见章节名称、children 归属和哪些材料通常单独编排。
- 当前招标文件是当前项目要求的权威来源，也是 `source_text` 的优先来源。
- 从历史目录学习来的每个 section 或 child，都必须尽量回到当前招标文件中寻找对应原文。
- 只有当前招标文件中找不到可靠对应原文时，才允许使用历史投标文件原文作为 `source_text` fallback。
- 当前项目补强项的 `source_text` 必须来自当前招标文件，不能来自历史投标文件。
- 顶层 `sections` 原则上保持历史商务标目录结构，不为匹配当前招标文件不稳定目录块而重排。
- `review_items` 只记录完成目录判断后仍影响目录项存在、归属或状态的人工审核问题。
- `required_status` 只表达该目录项在当前目录中的提交状态，只能为“必要”“可选”“待确认”。

### source_text 匹配优先级

1. 当前招标文件明确对应原文：投标文件格式、提交要求、材料名称、表格名称、承诺要求、资格/符合性/评分/前附表/特殊条款等。
2. 当前招标文件宽泛对应原文：能证明目录项必要性但与历史目录名称不完全一致；此时将 `required_status` 设为“待确认”或写入 `review_items`。
3. 历史投标文件原文 fallback：仅在当前招标文件找不到可靠对应原文时使用，并在 `outline_source`、`context` 或 `review_items` 中说明来源，避免误认为来自当前招标文件。

## 执行步骤

### 1. 定位并学习历史商务标投标文件目录

历史文件通常在当前工作目录下，文件名可能包含：

- 投标文件商务文件
- 商务文件
- 商务标
- 投标文件

不要把“招标文件”误认为历史商务标投标文件。如果用户明确指定历史文件，优先使用用户指定文件。

优先使用 `scripts/prepare_history_bid_outline_inputs.py` 整理历史目录候选：

```bash
python scripts/prepare_history_bid_outline_inputs.py <历史商务标投标文件.docx> --output history_bid_outline_inputs.json
```

该脚本负责读取历史商务标 DOCX，输出：

- `document_name`：历史文件名。
- `blocks`：历史文件原文块。
- `outline_source`：历史目录或标题结构来源，可能包含 `source_type` 和 `history_document_name`。
- `outline_candidates`：候选目录项、层级、历史原文证据。

脚本只提供候选和历史原文 fallback 证据，不直接生成 `outline.json`，不替代 AI 判断，不把历史原文默认当作最终 `source_text`。

### 2. 从历史商务标生成目录结构草案

基于 `history_bid_outline_inputs.json` 和 AI 对历史文件的理解，生成内部目录结构草案。

重点学习：

- 顶层 sections 顺序。
- 层级关系。
- 常见章节名称。
- children 归属。
- 哪些材料通常应单独编排。

不要为了匹配当前招标文件中的“投标文件格式”“响应文件格式”等不稳定目录块而重排历史目录结构。

### 3. 分析当前招标文件，形成 tender_map

继续使用 `scripts/prepare_tender_map_inputs.py`、`references/expert-checklist.md`、`scripts/get_context_block.py` 等现有工具分析当前招标文件。

```bash
python scripts/prepare_tender_map_inputs.py <招标文件.docx> --expert-checklist references/expert-checklist.md --output tender_map_inputs.json
```

该脚本只提供原文块、表格结构、重点区域切片和专家清单命中候选，不替代 AI 的 `tender_map` 和目录判断。

当前招标文件重点用于识别：

- 项目名称、标段、投标人类型、联合体、保证金、有效期等上下文。
- 特殊条款、特殊约定。
- 必须承诺项、必须响应项、必须提交材料。
- 表格中隐藏的提交要求。
- 废标条款。
- 资格审查要求。
- 符合性审查要求。
- 商务评分相关证明材料。
- 与历史目录草案中每个目录项对应的当前招标文件原文证据。

第 3 步不要把所有发现写入 `review_items`。只有后续步骤完成目录判断后仍无法确定的问题，才进入最终 `outline.json.review_items`。

#### 专家清单与参考样例

- `references/expert-checklist.md` 是可持续补充的专家经验清单，用于指导重点区域识别，不是硬编码目录规则。
- `references/outline.example.json` 是 `outline.json` 输出格式样例，可用于理解 schema，但不要照抄示例内容。

### 4. 为历史目录草案匹配当前招标文件 source_text

对每个从历史目录学习来的 section 或 child：

1. 先在当前招标文件 `tender_map` 中查找对应原文。
2. 优先匹配投标文件格式章节、投标文件组成、资格/符合性审查、评分标准、前附表、特殊条款、表格标题、材料提交要求等位置。
3. 若找到明确对应原文，使用当前招标文件原文作为 `source_text`。
4. 若只能找到宽泛对应原文，使用该宽泛原文作为 `source_text`，并将该项 `required_status` 设为“待确认”或在 `review_items` 中提示人工确认。
5. 若完全找不到可靠对应原文，才使用历史投标文件原文作为 `source_text`，并在 `context` 或 `review_items` 中说明该项来源于历史投标文件，当前招标文件未找到明确对应要求。

复核上下文时优先使用：

```bash
python scripts/get_context_block.py tender_map_inputs.json --text <关键词或原文> --format md
```

`source_text` 必须逐字复制来源原文，不得重组、改写、补全或调整编号位置。`title` 可以参考历史目录名称并做必要清理，但不得把无法证明的内容写成当前招标文件原文。

### 5. 用当前招标文件补强历史目录

如果当前招标文件中的要求已经被历史目录明确覆盖，不重复新增。

如果当前招标文件中的要求只是规则性条款，例如签字盖章、报价唯一、不得偏离、评分规则等，不要直接拆成目录项。

如果某项要求对应可单独提交、可单独编排、可单独审查的材料，例如承诺书、声明、证明材料、表格、截图、证书、合同、报告等，可以补充为 children。

优先把补强项放入已有历史顶层 section 的 `children`。原则上不要新增顶层 section；若当前招标文件明确要求提交但历史顶层目录完全无法承载，应写入 `review_items`，不要擅自新增顶层 section。

展开组合型目录项或补强 children 时，可继续使用：

```bash
python scripts/extract_format_children_candidates.py tender_map_inputs.json \
  --parent-source-text "附件7A 商务部分摘要表" \
  --next-sibling-source-text "附件7B" \
  --output children_candidates.json
```

也可在更可靠时使用 `--parent-title`、`--parent-section-id`、`--start-block-id`、`--end-before-block-id`。脚本只读取 `tender_map_inputs.json`，只输出候选，不直接生成 `outline.json`，不决定最终 children。

进入 `children` 的条件：

- 位于可靠的当前招标文件原文范围内。
- 是投标人需要单独填写、提交、后附或证明的材料单位。
- 可单独编排、可单独审查。
- 没有被现有 section 或 children 明确覆盖。
- 有当前招标文件逐字 `source_text`。

不进入 `children` 的情况：

- 只是评分规则。
- 只是签字盖章要求。
- 只是报价唯一性、不得偏离等规则性条款。
- 只是说明文字或填写提示。
- 已被更上层或更明确的目录项覆盖。

处理多标段、多报价表、多货物规格表等情况时，可依据 `tender_map`、`children_candidates.json` 和 `user_confirmed_inputs.json` 生成或标记相应 children；不能确定时，相关 section 的 `required_status` 标为“待确认”，并视情况写入 `review_items`。

### 6. 输出 outline.json

如果用户要求创建文件或提供了输出目录，则写入名为 `outline.json` 的文件；否则只返回 `outline.json` 的 JSON 内容。

无论写入文件还是直接返回，内容都必须是一个 JSON 对象，不要添加解释、Markdown 代码块、目录说明或正文内容。

`review_items` 是 `outline.json` 的一部分，只记录最终仍需要人工确认的目录判断问题。

## outline.json schema

参考完整样例见 `references/outline.example.json`。顶层结构：

```json
{
  "schema_version": "business_bid_outline.v1",
  "document_name": "招标文件名称",
  "outline_source": {},
  "context": {},
  "sections": [],
  "review_items": []
}
```

字段说明：

- `schema_version`：固定为 `business_bid_outline.v1`。
- `document_name`：当前招标文件名称，只写文件名或用户提供的文档名。
- `outline_source`：主目录结构学习来源。
  - `section_title`：AI 判断出的目录结构来源说明，通常为历史商务标目录或历史商务标标题结构。
  - `source_text`：用于学习顶层目录结构的历史商务标目录块或标题结构原文。
  - `confidence`：只能是 `high` / `medium` / `low`。
  - `source_type`：可选，建议使用 `history_bid_toc`、`history_bid_headings`、`history_bid_unknown`、`tender_matched`、`tender_format_toc`。
  - `history_document_name`：可选，历史商务标投标文件名；当目录结构来自历史文件时建议填写。
- `context`：只记录对目录展开或后续正文生成有明显影响的关键上下文，key 使用英文 snake_case，每项尽量包含 `value` 或 `summary` 以及 `source_text`。
- `sections`：最终目录树，数组顺序就是商务标目录顺序。
- `review_items`：只记录目录生成完成后仍需人工审核的目录判断问题。

section 字段规则：

- `id`：稳定目录项 ID，建议 `sec-001`、`sec-001-001`。
- `title`：目录标题，可参考历史商务标目录名称。
- `level`：顶层为 `1`，子项为 `2`。
- `required_status`：只能是“必要”“可选”“待确认”，表示该目录项在当前目录中的提交状态。
  - “必要”：当前招标文件明确要求提交，或历史目录项已被当前招标文件明确/宽泛要求证明应纳入。
  - “可选”：仅在特定条件下提交，例如联合体、代理商、备选方案等情形。
  - “待确认”：该目录项已有依据进入目录树，但是否适用、是否保留或是否独立列出仍需人工判断。
- `source_text`：该目录项对应的逐字原文证据。优先来自当前招标文件；只有当前招标文件找不到可靠对应原文时，才可使用历史投标文件原文 fallback，并说明原因。
- `children`：子目录项数组，没有则为空数组。

review_items 字段规则：

- `message`：说明目录生成中需要人工审核的问题。
- `source_text`：触发该问题的当前招标文件原文；若问题是历史 fallback 来源，也可引用对应历史原文并在 `message` 中明确说明。
- `suggested_section_id`：最可能承载该要求的 section.id；完全无法判断时为 `null`。
- `required_status`：只能是“必要”“可选”“待确认”。

## 输出要求

如果用户要求创建文件或提供了输出目录，最终交付为 `outline.json` 文件；否则最终响应只输出 `outline.json` 的 JSON 内容。

生成 `outline.json` 后，建议运行 schema 校验：

```bash
python scripts/validate_outline.py outline.json
```

如果已有 `tender_map_inputs.json`，建议继续检查来自当前招标文件的 `source_text` 是否可追溯：

```bash
python scripts/check_source_text.py outline.json tender_map_inputs.json
```

若有少量 `source_text` 合理来自历史投标文件 fallback，`check_source_text.py` 可能报告 unmatched；必须在 `context` 或 `review_items` 中确认这些项已说明历史来源和原因。

不要输出：

- 解释文字
- Markdown 代码块
- 商务标正文
- Markdown 目录
- 额外文件清单
- 内部 `tender_map`

## 质量检查清单

输出前逐项自检：

1. 是否先学习历史商务标目录？
2. 是否为每个历史目录项尝试匹配当前招标文件 `source_text`？
3. 是否避免把招标文件不稳定目录块作为主目录来源？
4. 顶层 `sections` 是否保持历史目录结构？
5. 当前招标文件特殊条款、约定、必须承诺、必须提交材料是否已检查？
6. 废标、资格审查、符合性审查、商务评分线索是否都已检查？
7. 新增 children 是否可单独编排、可单独审查？
8. 规则性条款是否避免被直接拆成目录项？
9. `source_text` 是否优先来自当前招标文件？
10. 使用历史投标文件 `source_text` 的项是否已说明原因？
11. `required_status` 是否只使用“必要”“可选”“待确认”？
12. 是否已通过 `scripts/validate_outline.py`？
13. 如果已有 `tender_map_inputs.json`，是否已用 `scripts/check_source_text.py` 检查当前招标文件来源的 `source_text` 可追溯？
