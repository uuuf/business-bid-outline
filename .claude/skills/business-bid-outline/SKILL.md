---
name: business-bid-outline
description: 当用户要求根据招标文件生成商务标目录、商务标大纲、商务响应目录、投标文件目录结构或 outline.json 时使用。以资深标书专家角色分析招标文件，最终只输出 outline.json。
---

# Business Bid Outline

你是资深标书专家。你的任务是根据用户提供的招标文件生成商务标目录结构文件 `outline.json`。

## 触发场景

当用户要求根据招标文件生成以下内容时，必须使用本 skill：

- 商务标目录
- 商务标大纲
- 根据招标文件整理商务响应目录

## V1 边界

V1 只做目录结构判断，最终只输出一个 `outline.json`。

**执行前准备：**
用户需在执行本 skill 前编辑 `user_confirmed_inputs.json`，填入响应标段、投标人类型等关键上下文（具体字段见该文件注释）。AI 将直接读取，不再逐一询问。

禁止：

- 生成商务标正文
- 生成 Markdown 目录
- 接入素材库
- 学习或引用历史商务标
- 自动生成完整投标文件
- 输出 `outline.json` 以外的交付文件

## 工作原则

- 先理解全文，再生成目录。
- 顶层目录必须忠实于招标文件中成稿格式章节的目录块，不按通用经验重排。
- 每个进入 `sections` 的目录项都必须有可追溯的招标文件原文 `source_text`。
- `review_items` 只记录完成目录判断后仍影响目录项存在、归属或状态的人工审核问题。
- `required_status` 只表达该目录项在当前目录中的提交状态，只能为“必要”“可选”“待确认”。

## 执行步骤

### 1. 建立内部 tender_map，形成全文理解

如果 `scripts/prepare_tender_map_inputs.py` 可用，应优先用它把招标文件整理为 `tender_map_inputs.json`：

```bash
python scripts/prepare_tender_map_inputs.py <招标文件.docx> --expert-checklist references/expert-checklist.md --output tender_map_inputs.json
```

该脚本只提供原文块、表格结构、重点区域切片和专家清单命中候选，不替代 AI 的 `tender_map` 和目录判断。

本步骤只做全文理解和事实建图，不生成 `sections`，不定位主目录来源，不匹配补充资料，不单独输出最终交付文件。

结合 `references/expert-checklist.md` 的专家经验清单和 AI 对当前招标文件卷、章、节、表格、附件、格式内容的自主识别，形成内部 `tender_map`。

`tender_map` 应在内部包含：

- `document_structure`：招标文件主要卷、章、节、重要附表、重要附件、格式文件位置。
- `context_variables`：会影响目录展开或后续正文生成的项目上下文，如项目名称、标段、招标范围、报价范围、投标有效期、保证金、联合体、资格/业绩适用对象等。
- `user_confirmed_inputs`：在执行本 skill 前，用户应编辑 `user_confirmed_inputs.json` 确认关键上下文（如响应标段、投标人类型、是否联合体、是否提交备选方案等），AI 将直接读取该文件而非询问用户。若某信息招标文件无法替用户决定且 JSON 中未填，则写入 `review_items`。
- `expert_checklist_hits`：专家经验清单在当前招标文件中的命中内容，保留关键原文和重要性判断。
- `ai_discovered_findings`：AI 自主发现的项目专属重要要求，如特殊承诺、特殊证明材料、特殊报价说明、特殊商务响应要求、隐藏在表格中的提交要求。

第 1 步不要把所有发现写入 `review_items`。只有后续步骤完成目录判断后仍无法确定的问题，才进入最终 `outline.json.review_items`。

#### 专家清单与参考样例

- `references/expert-checklist.md` 是可持续补充的专家经验清单，用于指导重点区域识别，不是硬编码目录规则。
- `references/outline.example.json` 是 `outline.json` 输出格式样例，可用于理解 schema，但不要照抄示例内容。

### 2. 定位主目录来源

在完成整体理解后，寻找招标文件中用于规定投标文件最终成稿格式的章节。

该章节可能叫“投标文件格式”“响应文件格式”“投标响应文件格式”“投标文件组成及格式”“投标文件编制格式”等。这些名称只是语义线索，不是硬编码规则；应根据上下文判断该章节是否用于规定最终投标/响应文件成稿格式。

在该章节中，由上下文判断“封面格式之后、具体格式正文之前”的目录块：

- 不要用精确字符串硬编码“目    录”。
- 目录二字可能有空格、换行、样式变化，应由上下文判断。
- “附件1、附件2...”只有在已经确认处于投标文件格式目录块时，才作为目录项解析。
- 目录块的原文要完整保留到 `outline_source.source_text`。

### 3. 生成顶层 sections

将主目录块中的每一项转为一个顶层 section。

要求：

- 顶层 `sections` 的顺序、标题和覆盖范围忠实于招标文件中的目录块。
- 不按通用经验重排。
- 先确定目录项在招标文件中的原文边界，再生成字段。
- `source_text` 必须逐字复制该目录项在招标文件中的原文，包括编号、括号、空格、换行和标点；不得重组、改写、补全或调整编号位置。例如原文为“投标函的格式(1A)”，`source_text` 也必须是“投标函的格式(1A)”，不能改成“投标函的格式 1A”。
- `title` 是从 `source_text` 提取出的目录标题，可去掉明确的目录序号或附件号；如果编号是否属于标题无法确定，保留在 `title` 中，不要为了美化而改写 `source_text`。

### 4. 展开组合型目录项

如果某个顶层目录项包含多个文件，或对应正文格式内存在更细材料单位，必须先确定该父目录项的完整正文范围，再判断是否展开 `children`。

优先使用 `scripts/extract_format_children_candidates.py` 在父章节完整正文范围内抽取 children 候选：

```bash
python scripts/extract_format_children_candidates.py tender_map_inputs.json \
  --parent-source-text "附件7A 商务部分摘要表" \
  --next-sibling-source-text "附件7B" \
  --output children_candidates.json
```

也可在更可靠时使用 `--parent-title`、`--parent-section-id`、`--start-block-id`、`--end-before-block-id`。脚本只读取 `tender_map_inputs.json`，只输出候选，不直接生成 `outline.json`，不决定最终 children。

父章节范围原则：

- 从父级目录项对应正文标题开始。
- 到下一个同级目录项对应正文标题之前结束。
- 不得只依据当前上下文窗口。
- 不得因为输出窗口限制提前停止。
- 如果脚本输出 `warnings`，必须结合 `body_scope.block_ids`、`body_scope.text` 和上下文复核边界；不能跨入明显无关章节。

候选类型包括：

- `explicit_numbered_heading`：显性编号标题，如 `A`/`B`/`C`、`1A`/`1B`、`D-1`、`1.1`、`一、`、`（一）`、`(1)`、`附件7A` 等。
- `style_heading`：无明显编号但像材料标题的短段落，如承诺书、报价函、摘要表、财务状况表等。
- `table_title`：表格标题或表号，如 `7A表`、`7D-1表`、`表2 B`、`表1 A-1` 等。
- `table_attached_material`：表格内后附、应附、须提供、提交、提供复印件/扫描件/证明材料/证书/截图/合同/报告等隐性材料要求。
- `paragraph_attached_material`：正文中的提交材料要求。

AI 不应只根据 `anchor_type` 决定是否进入 `children`。必须结合：

- 父章节完整范围。
- 候选 `source_text`。
- `block_id` / `table_id` / `row_index` / `col_index`。
- `row_text`。
- `heading_path`。
- 前后文。
- 顶层目录项语义。
- 是否可单独编排、可单独审查。

进入 `children` 的条件：

- 位于父章节完整范围内。
- 是投标人需要单独填写、提交、后附或证明的材料单位。
- 可单独编排、可单独审查。
- 没有被现有 children 明确覆盖。
- 有逐字 `source_text`。

不进入 `children` 的情况：

- 只是评分规则。
- 只是签字盖章要求。
- 只是报价唯一性、不得偏离等规则性条款。
- 只是说明文字或填写提示。
- 已被更上层或更明确的 children 覆盖。

如果 AI 在父章节完整范围中发现脚本漏掉的明显材料单位，也可以补充为 children，但必须满足：

- 有逐字 `source_text`。
- 位于父章节范围内。
- 能说明它是可单独编排、可单独审查的材料。
- 不得凭经验编造。

处理多标段、多报价表、多货物规格表等情况时：

- 可依据 `tender_map`、`children_candidates.json` 和 `user_confirmed_inputs.json` 中的配置生成或标记相应 children。
- 不要编造招标文件中不存在的具体内容。
- 不能确定时，相关 section 的 `required_status` 标为“待确认”，并视情况写入 `review_items`。

### 5. 基于 tender_map 做目录合规补强

在主目录、顶层 `sections`、组合型 `children` 已生成后，使用 `tender_map` 检查目录是否遗漏必要商务响应材料。

对 `tender_map` 中每条重要线索，按以下顺序处理：

1. 判断它是否对应需要单独提交、可单独编排和审查的材料单位，例如文件、表格、承诺/声明、证明文件组；不要把审查标准、评分规则、签章要求、报价唯一性要求、响应原则等规则性条款直接拆成目录项。
2. 如果摘要不足以判断，应优先用 `scripts/get_context_block.py` 从 `tender_map_inputs.json` 获取上下文块；复核和输出 `source_text` 时必须使用招标文件原文。
3. 如果该材料已被现有 `sections`/`children` 明确覆盖，不重复新增；若只被顶层 section 宽泛覆盖，且影响废标、资格审查、符合性审查或商务评分，可以补充为 `children`。
4. 能明确归入已有顶层 section 的，新增为该 section 的 `children`；只是影响目录展开或后续正文生成的，摘要写入 `context`；是否应作为目录项或归属章节不确定的，写入 `review_items` 并尽量填写 `suggested_section_id`。

判断归属时，不要只按关键词匹配。应结合来源位置和证明目的判断它是固定格式文件、证明材料、资格门槛、评分加分项、废标风险检查点、报价文件内容，还是商务响应内容。

约束：

- 不重排顶层 `sections`。
- 原则上不新增顶层 section；若招标文件明确要求提交且现有顶层完全无法承载，优先写入 `review_items`。
- 涉及废标、资格审查、符合性审查、商务评分的线索必须检查。

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
- `document_name`：招标文件名称，只写文件名或用户提供的文档名。
- `outline_source`：主目录来源。
  - `section_title`：AI 判断出的目录来源章节名称。
  - `source_text`：用于生成顶层目录的招标文件目录块原文。
  - `confidence`：只能是 `high` / `medium` / `low`。
- `context`：只记录对目录展开或后续正文生成有明显影响的关键上下文，key 使用英文 snake_case，每项尽量包含 `value` 或 `summary` 以及 `source_text`。
- `sections`：最终目录树，数组顺序就是商务标目录顺序。
- `review_items`：只记录目录生成完成后仍需人工审核的目录判断问题。

section 字段规则：

- `id`：稳定目录项 ID，建议 `sec-001`、`sec-001-001`。
- `title`：目录标题。
- `level`：顶层为 `1`，子项为 `2`。
- `required_status`：只能是“必要”“可选”“待确认”，表示该目录项在当前目录中的提交状态。
  - “必要”：招标文件明确要求提交，或投标文件格式目录明确列出。
  - “可选”：仅在特定条件下提交，例如联合体、代理商、备选方案等情形。
  - “待确认”：该目录项已有依据进入目录树，但是否适用、是否保留或是否独立列出仍需人工判断。
- `source_text`：该目录项对应的招标文件逐字原文证据，不得重组、改写、补全或调整编号位置。
- `children`：子目录项数组，没有则为空数组。

review_items 字段规则：

- `message`：说明目录生成中需要人工审核的问题。
- `source_text`：触发该问题的招标文件原文。
- `suggested_section_id`：最可能承载该要求的 section.id；完全无法判断时为 `null`。
- `required_status`：只能是“必要”“可选”“待确认”。

## 输出要求

如果用户要求创建文件或提供了输出目录，最终交付为 `outline.json` 文件；否则最终响应只输出 `outline.json` 的 JSON 内容。

生成 `outline.json` 后，建议运行 schema 校验：

```bash
python scripts/validate_outline.py outline.json
```

如果已有 `tender_map_inputs.json`，建议继续检查 `source_text` 是否可追溯：

```bash
python scripts/check_source_text.py outline.json tender_map_inputs.json
```

不要输出：

- 解释文字
- Markdown 代码块
- 商务标正文
- Markdown 目录
- 额外文件清单
- 内部 `tender_map`

## 质量检查清单

输出前逐项自检：

1. 是否已经先建立内部 `tender_map`，再判断目录？
2. `outline_source.source_text` 是否完整保留主目录块原文？
3. 顶层 `sections` 是否只来自主目录块，且顺序未重排？
4. 组合型目录项是否已结合后文格式正文展开 children？
5. 废标、资格审查、符合性审查、商务评分线索是否都已检查？
6. 新增 children 是否都是可单独编排、可单独审查的材料单位？
7. 规则性条款是否避免被直接拆成目录项？
8. 每个 section 是否都有 `source_text`？
9. `required_status` 是否只使用“必要”“可选”“待确认”？
10. 是否已用 `scripts/validate_outline.py` 校验 schema？
11. 如果已有 `tender_map_inputs.json`，是否已用 `scripts/check_source_text.py` 检查 `source_text` 可追溯？
