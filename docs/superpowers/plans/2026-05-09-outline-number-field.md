# Outline Number Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `number` field to every `outline.json` section and teach the skill to inherit numbering patterns from historical business bid templates.

**Architecture:** Keep tender-file `source_text` as evidence, but use historical business bid template structure to learn numbering style and no-number headings. Add schema validation for `number`, update examples and guidance, and add tests covering numbered and unnumbered headings.

**Tech Stack:** Markdown skill docs, JSON schema-style validation in Python, DOCX preprocessing scripts using Python standard library OOXML parsing.

---

### Task 1: Snapshot Current Version

**Files:**
- Modify/create remote metadata only through Git.
- Commit tracked skill files and new skill helper scripts.

- [ ] **Step 1: Stage only repository-quality files**

Run:
```powershell
git add .gitignore .claude/skills/business-bid-outline/SKILL.md .claude/skills/business-bid-outline/references/outline.example.json .claude/skills/business-bid-outline/scripts/prepare_tender_map_inputs.py .claude/skills/business-bid-outline/scripts/resolve_source_text_candidates.py .claude/skills/business-bid-outline/scripts/test_generate_outline_candidates.py .claude/skills/business-bid-outline/scripts/test_prepare_tender_map_inputs.py .claude/skills/business-bid-outline/scripts/test_resolve_source_text_candidates.py docs/superpowers/plans/2026-05-09-outline-number-field.md
```
Expected: no generated outputs, `.docx`, `.vs`, `Search`, or `__pycache__` staged.

- [ ] **Step 2: Commit snapshot**

Run:
```powershell
git diff --cached --name-only
git commit -m "chore: snapshot business bid outline skill before numbering"
```
Expected: commit succeeds with only skill/source/test/plan files.

- [ ] **Step 3: Push to GitHub and tag**

Run:
```powershell
git remote add origin https://github.com/uuuf/business-bid-outline.git
git push -u origin master
git tag v3.1-before-number-field
git push origin v3.1-before-number-field
```
Expected: remote branch and tag created. If remote already exists, set-url instead of add.

### Task 2: Update Schema Contract

**Files:**
- Modify: `D:/Project/Cluade_Code/business-bid-outline/.claude/skills/business-bid-outline/SKILL.md`
- Modify: `D:/Project/Cluade_Code/business-bid-outline/.claude/skills/business-bid-outline/references/outline.example.json`
- Modify: `D:/Project/Cluade_Code/business-bid-outline/.claude/skills/business-bid-outline/scripts/validate_outline.py`

- [ ] **Step 1: Add `number` to every section in docs and example**

Rules:
- `number` is required on every section object.
- Use string for numbered headings, e.g. `"一"`, `"1.1"`, `"1.1.1"`.
- Use `null` for headings that intentionally have no numbering, e.g. `商务评分索引表`, `供货保障专题`.
- `number` comes from historical business bid heading style where available; it is not copied from tender `source_text` unless the tender defines final Word numbering style.

- [ ] **Step 2: Validate `number`**

Change `validate_outline.py` so each section requires `number`, and accepts only `str` or `null`.
Expected failures:
```json
{"id":"sec-001","title":"A","level":1,"required_status":"必要","source_text":"A","children":[]}
```
should fail with missing `number`.

### Task 3: Teach Historical Number Learning

**Files:**
- Modify: `D:/Project/Cluade_Code/business-bid-outline/.claude/skills/business-bid-outline/SKILL.md`
- Modify/create tests around `prepare_history_bid_outline_inputs.py` if script already supports heading extraction.

- [ ] **Step 1: Document numbering source priority**

Add guidance:
- First learn numbering pattern from historical business bid template.
- Preserve no-number headings observed in history.
- Generate missing sibling numbers by continuing the learned pattern only when the pattern is clear.
- Do not force numbering onto historical no-number headings.
- If numbering cannot be inferred, set `number: null` and put the uncertainty in `review_items` only when it affects Word formatting or section identity.

- [ ] **Step 2: Keep tender evidence separate**

Add warning:
- `source_text` remains tender/current evidence.
- `number` is layout/format metadata learned from historical template.
- Do not alter `source_text` to include or remove numbering for Word formatting.

### Task 4: Script Support and Tests

**Files:**
- Inspect/modify: `D:/Project/Cluade_Code/business-bid-outline/.claude/skills/business-bid-outline/scripts/prepare_history_bid_outline_inputs.py`
- Modify tests as needed.

- [ ] **Step 1: Ensure history extraction exposes number and title separately**

Expected historical outline item shape should include enough data for AI to infer:
```json
{
  "level": 1,
  "number": "一",
  "title": "投标函、法定代表人身份证明、授权委托书、廉洁自律承诺书",
  "raw_text": "一、投标函、法定代表人身份证明、授权委托书、廉洁自律承诺书"
}
```
For no-number headings:
```json
{
  "level": 1,
  "number": null,
  "title": "商务评分索引表",
  "raw_text": "商务评分索引表"
}
```

- [ ] **Step 2: Add regression tests**

Tests must cover:
- Chinese numeral top-level number extraction: `一、...`.
- Decimal second/third-level extraction: `1.1 ...`, `1.1.1 ...`.
- No-number heading remains `number: null`.
- Validator rejects missing `number`.

### Task 5: Verification and Commit

**Files:**
- All modified files from Tasks 2-4.

- [ ] **Step 1: Run tests**

Run:
```powershell
python .claude/skills/business-bid-outline/scripts/test_prepare_history_bid_outline_inputs.py
python .claude/skills/business-bid-outline/scripts/test_extract_format_children_candidates.py
python .claude/skills/business-bid-outline/scripts/test_prepare_tender_map_inputs.py
python .claude/skills/business-bid-outline/scripts/test_resolve_source_text_candidates.py
python -m py_compile .claude/skills/business-bid-outline/scripts/*.py
```
Expected: all tests pass and py_compile exits 0.

- [ ] **Step 2: Validate updated example**

Run:
```powershell
python .claude/skills/business-bid-outline/scripts/validate_outline.py .claude/skills/business-bid-outline/references/outline.example.json
```
Expected: validation passes.

- [ ] **Step 3: Commit numbering update**

Run:
```powershell
git add .claude/skills/business-bid-outline/SKILL.md .claude/skills/business-bid-outline/references/outline.example.json .claude/skills/business-bid-outline/scripts/validate_outline.py .claude/skills/business-bid-outline/scripts/prepare_history_bid_outline_inputs.py .claude/skills/business-bid-outline/scripts/test_prepare_history_bid_outline_inputs.py
git commit -m "feat: add outline section numbering metadata"
```
Expected: commit contains only numbering-related changes.
