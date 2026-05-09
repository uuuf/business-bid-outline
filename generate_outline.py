import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY_PATH = ROOT / "history_bid_outline_inputs.json"
TENDER_PATH = ROOT / "tender_map_inputs.json"
OUTLINE_PATH = ROOT / "outline.json"
CANDIDATES_PATH = ROOT / "source_text_candidates.json"

NECESSARY = "必要"
OPTIONAL = "可选"
CONFIRM = "待确认"

TOC_LINE_RE = re.compile(r"(?:\.{2,}|…{2,}|\s{2,}|\t)\s*\d+\s*$")
SIMPLE_PAGE_LINE_RE = re.compile(r"^.{2,80}\s+\d{1,4}\s*$")
SCOPE_ORDER = {
    "parent_context": 0,
    "format_area": 1,
    "high_value_area": 2,
    "broad_clause": 3,
    "full_text": 4,
}
FORMAT_HEADING_RE = re.compile(
    r"^(附件\s*\d+[A-Za-z]?(?:[-－]?\d+)?|附表\s*\d*[A-Za-z]?|表\s*\d+[A-Za-z]?(?:[-－]?\d+)?|\d+[A-Za-z](?:[-－]?\d+)?\s*表?|[A-Z](?:-\d+)?)[\s、．.]*\S*"
)
ATTACHED_TERMS = ["后附", "另附", "应附", "须附", "提供", "提交", "复印件", "扫描件", "证明材料"]
NUMBERED_ITEM_RE = re.compile(r"^\s*(?:\d+|[一二三四五六七八九十]+)[、．.]\s*\S+")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def compact(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize(text):
    return re.sub(r"\s+", "", text or "").lower()


def title_core(title):
    value = compact(title)
    patterns = [
        r"^[一二三四五六七八九十]+[、．.]\s*",
        r"^\d+(?:\.\d+)*\s*",
        r"^附件\s*\d+[A-Z]?(?:[-－]?\d+)?\s*",
        r"^\d+[A-Z]?(?:[-－]?\d+)?表\s*",
    ]
    for pattern in patterns:
        value = re.sub(pattern, "", value)
    return compact(value)


def build_history_tree(candidates):
    roots = []
    stack = []
    for candidate in candidates:
        node = {
            "title": compact(candidate.get("title_hint", "")),
            "number": candidate.get("number"),
            "level": int(candidate.get("level") or 1),
            "candidate": candidate,
            "children": [],
        }
        if not node["title"]:
            continue
        while stack and stack[-1]["level"] >= node["level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots


def collect_texts(tender):
    texts = []
    for block in tender.get("blocks", []):
        text = compact(block.get("text", ""))
        if text:
            texts.append(("block", text))
    for zone in tender.get("zones", []):
        text = compact(zone.get("text", ""))
        if text:
            texts.append(("zone", text))
    for table in tender.get("tables", []):
        for key in ("nearby_heading", "nearby_caption"):
            text = compact(table.get(key, ""))
            if text:
                texts.append(("table", text))
        for row in table.get("rows", []):
            text = compact(row.get("row_text", ""))
            if text:
                texts.append(("table", text))
            for cell in row.get("cells", []):
                cell_text = compact(cell.get("text", ""))
                if cell_text:
                    texts.append(("table", cell_text))
    return texts


def first_contains(texts, terms, min_len=0):
    terms = [term for term in terms if term]
    if not terms:
        return ""
    for _, text in texts:
        if len(text) < min_len:
            continue
        if all(term in text for term in terms):
            return text
    return ""


def block_texts(tender):
    return [compact(block.get("text", "")) for block in tender.get("blocks", []) if compact(block.get("text", ""))]


def first_block_between(blocks, start_term, end_term, terms):
    in_scope = False
    for text in blocks:
        if start_term in text:
            in_scope = True
            continue
        if in_scope and end_term and end_term in text:
            in_scope = False
            continue
        if in_scope and all(term in text for term in terms):
            return text
    return ""


def attachment_1_child_source(blocks, title):
    source_specs = [
        (["投标函"], ["投标函", "1A"]),
        (["法定代表人", "身份证明"], ["法定代表人", "身份证明", "1B"]),
        (["授权"], ["授权", "1C"]),
        (["廉洁自律"], ["廉洁自律", "1D"]),
    ]
    for title_terms, source_terms in source_specs:
        if all(term in title for term in title_terms):
            return first_block_between(blocks, "附件1 投标函", "附件2 投标价格表", source_terms)
    return ""


def attachment_7a_child_source(blocks, title):
    source_specs = [
        (["营业执照"], ["营业执照"]),
        (["企业资质"], ["资质"]),
        (["认证体系"], ["认证体系"]),
        (["组织机构"], ["组织机构"]),
        (["基本存款账户"], ["基本存款账户"]),
    ]
    for title_terms, source_terms in source_specs:
        if all(term in title for term in title_terms):
            attached = first_block_between(blocks, "附件7A 商务部分摘要表", "附件7B", [*source_terms, "后附"])
            if attached:
                return attached
            return first_block_between(blocks, "附件7A 商务部分摘要表", "附件7B", source_terms)
    return ""


def form_child_source(blocks, title, parent_title):
    if "投标人/工厂简介" in parent_title:
        return ""
    if "近年财务数据" in parent_title:
        for marker in ["7D-1表 近年财务状况表", "7D-2表 资产负债表", "7D-3表 损益表", "7D-4表 现金流量表"]:
            source = first_block_between(blocks, "附件7D", "附件7E", [marker])
            if source:
                return source
    if "资信证明、商业信誉" in parent_title:
        if "资信证明" in title:
            source = first_block_between(blocks, "附表3：商务评分标准表", "第三卷 合同条款", ["银行资信证明"])
            if source:
                return source
        if "商业信誉" in title:
            source = first_block_between(blocks, "附件7E", "附件7F", ["获奖"])
            if source:
                return source
    if "符合招标公告及招标文件要求的业绩情况" in parent_title:
        if "240小时" in title:
            return first_block_between(blocks, "附件7I", "附件8", ["7I-1"])
        if "合同业绩" in title:
            return first_block_between(blocks, "附件7I", "附件8", ["7I-2"])
        if "正在供货" in title:
            return ""
    return ""


def build_source_resolver(tender):
    texts = collect_texts(tender)
    blocks = block_texts(tender)
    format_sources = {}
    for _, text in texts:
        for marker in [
            "附件1 投标函",
            "附件2 投标价格表",
            "附件3 货物规格一览表",
            "附件4 商务条款偏差表",
            "附件5 投标保证金格式",
            "附件6 履约保证函格式承诺书",
            "附件7 资格证明文件",
            "附件8 开标价格表",
        ]:
            if marker in text and marker not in format_sources:
                format_sources[marker] = text
        for marker in [
            "商务部分摘要表",
            "投标单位股权结构说明",
            "投标人/工厂简介",
            "资产负债表、损益表、现金流量表",
            "资信证明",
            "败诉的设备买卖合同",
            "关于企业状况的声明函",
            "全国企业信用信息公示系统",
            "符合招标公告及招标文件要求的业绩情况",
            "说明技术来源",
            "保密承诺书",
        ]:
            if marker in text and marker not in format_sources:
                format_sources[marker] = text

    aliases = [
        (["商务评分索引表"], ["商务评分", "评分标准"]),
        (["供货保障专题"], ["供货保障"]),
        (["投标函"], ["附件1 投标函"]),
        (["法定代表人", "身份证明"], ["附件1 投标函"]),
        (["授权"], ["附件1 投标函"]),
        (["廉洁自律"], ["附件1 投标函"]),
        (["投标专用章"], ["投标专用章"]),
        (["投标价格表"], ["附件2 投标价格表"]),
        (["货物规格一览表"], ["附件3 货物规格一览表"]),
        (["商务条款偏差表"], ["附件4 商务条款偏差表"]),
        (["投标保证金"], ["附件5 投标保证金格式"]),
        (["履约保证函"], ["附件6 履约保证函格式承诺书"]),
        (["资格证明文件"], ["附件7 资格证明文件"]),
        (["商务部分摘要表"], ["商务部分摘要表"]),
        (["营业执照"], ["营业执照"]),
        (["企业资质"], ["企业资质"]),
        (["认证体系"], ["认证体系"]),
        (["组织机构"], ["组织机构"]),
        (["基本存款账户"], ["基本存款账户"]),
        (["股权结构"], ["投标单位股权结构说明"]),
        (["工厂简介"], ["投标人/工厂简介"]),
        (["公司基本情况"], ["投标人/工厂简介"]),
        (["生产能力"], ["生产能力"]),
        (["纳税信用"], ["纳税信用"]),
        (["质量管理"], ["质量管理"]),
        (["获奖"], ["获奖"]),
        (["专利"], ["专利"]),
        (["财务"], ["资产负债表、损益表、现金流量表"]),
        (["资信证明"], ["资信证明"]),
        (["商业信誉"], ["商业信誉"]),
        (["诉讼", "仲裁"], ["败诉的设备买卖合同"]),
        (["企业状况", "声明函"], ["关于企业状况的声明函"]),
        (["信用", "查询结果"], ["全国企业信用信息公示系统"]),
        (["业绩情况"], ["符合招标公告及招标文件要求的业绩情况"]),
        (["完成的", "风电机组"], ["符合招标公告及招标文件要求的业绩情况"]),
        (["正在供货"], ["符合招标公告及招标文件要求的业绩情况"]),
        (["技术来源"], ["说明技术来源"]),
        (["开标价格表"], ["附件8 开标价格表"]),
        (["保密承诺书"], ["保密承诺书"]),
    ]

    def resolve(title, parent_title=""):
        if "附件1" in parent_title or "投标函、法定代表人" in parent_title:
            scoped = attachment_1_child_source(blocks, title)
            if scoped:
                return scoped, True
        if "商务部分摘要表" in parent_title:
            scoped = attachment_7a_child_source(blocks, title)
            if scoped:
                return scoped, True
        scoped = form_child_source(blocks, title, parent_title)
        if scoped:
            return scoped, True
        if "投标人/工厂简介" in parent_title:
            return "", False

        core = title_core(title)
        norm_core = normalize(core)
        if not core:
            return "", False

        if "资信证明" in title and "商业信誉" in title:
            combined = first_contains(texts, ["资信证明", "商业信誉"])
            if combined:
                return combined, True

        direct = first_contains(texts, [core])
        if direct:
            return direct, True

        for title_terms, source_terms in aliases:
            if all(term in title for term in title_terms) or all(normalize(term) in norm_core for term in title_terms):
                for term in source_terms:
                    if term in format_sources:
                        return format_sources[term], True
                source = first_contains(texts, source_terms)
                if source:
                    return source, True

        tokens = [token for token in re.split(r"[、，,（）()\s/]+", core) if len(normalize(token)) >= 3]
        for token in sorted(tokens, key=len, reverse=True):
            source = first_contains(texts, [token])
            if source:
                return source, True
        return "", False

    return resolve


def make_id(path):
    return "sec-" + "-".join(f"{part:03d}" for part in path)


def status_for_title(title, matched):
    if any(term in title for term in ["授权委托", "授权书", "技术支持方(如有)", "如有"]):
        return OPTIONAL if matched else CONFIRM
    if title.startswith("9.19"):
        return CONFIRM
    return NECESSARY if matched else CONFIRM


def is_toc_like_source(text):
    stripped = (text or "").strip()
    if normalize(stripped) in {"目录", "目次"}:
        return True
    return bool(TOC_LINE_RE.search(stripped) or SIMPLE_PAGE_LINE_RE.match(stripped))


def candidate_quality_penalty(candidate):
    text = candidate.get("source_text", "")
    penalty = 0
    if is_toc_like_source(text):
        penalty += 100
    if len(text) > 800:
        penalty += 100
    return penalty


def looks_like_format_heading(text):
    stripped = (text or "").strip()
    return len(stripped) <= 90 and bool(FORMAT_HEADING_RE.match(stripped))


def is_table_row_candidate(candidate):
    return candidate.get("source_type") == "table_row" or candidate.get("block_type") == "table_row"


def is_table_cell_candidate(candidate):
    return candidate.get("source_type") == "table_cell" or candidate.get("block_type") == "table_cell_marker"


def evidence_granularity_bonus(candidate):
    text = candidate.get("source_text", "")
    bonus = 0
    if candidate.get("scope") == "parent_context" and NUMBERED_ITEM_RE.match(text):
        bonus += 0.5
    if is_table_cell_candidate(candidate):
        bonus += 0.6
    elif is_table_row_candidate(candidate):
        bonus -= 0.6
    if any(term in text for term in ATTACHED_TERMS):
        bonus += 0.4
    if "|" in text or len(text) > 120:
        bonus -= 0.3
    if looks_like_format_heading(text) and not any(term in text for term in ATTACHED_TERMS):
        bonus += 0.4
    if candidate.get("scope") == "format_area" and looks_like_format_heading(text):
        bonus += 0.7
    return bonus


def candidate_priority(candidate):
    scope = candidate.get("scope")
    priority = SCOPE_ORDER.get(scope, 9)
    priority += candidate_quality_penalty(candidate)
    priority -= evidence_granularity_bonus(candidate)
    return (priority, -float(candidate.get("score", 0)), candidate.get("source_text", ""))


def load_candidates(path):
    if not path or not Path(path).exists():
        return {}
    data = load_json(path)
    return {item.get("id"): item for item in data.get("items", [])}


def choose_candidate(section_id, candidates_by_id, parent_source_text=""):
    item = candidates_by_id.get(section_id) or {}
    candidates = [candidate for candidate in item.get("candidates", []) if candidate.get("source_text")]
    if parent_source_text:
        parent_norm = normalize(parent_source_text)
        filtered = [candidate for candidate in candidates if normalize(candidate.get("source_text", "")) != parent_norm]
        if filtered:
            candidates = filtered
    candidates = [candidate for candidate in candidates if candidate_quality_penalty(candidate) < 100]
    if not candidates:
        return "", False, ""
    best = sorted(candidates, key=candidate_priority)[0]
    return best.get("source_text", ""), True, best.get("scope", "")


def fallback_source_text(node):
    source_text = compact(node["candidate"].get("source_text", ""))
    if is_toc_like_source(source_text) or re.search(r"\s+\d{1,4}\s*$", source_text or ""):
        return compact(node.get("title", ""))
    return source_text


def convert_node(node, path, resolve_source, fallback_items, parent_title="", candidates_by_id=None, parent_source_text=""):
    section_id = make_id(path)
    source_text, matched, scope = choose_candidate(section_id, candidates_by_id or {}, parent_source_text)
    if not source_text:
        source_text, matched = resolve_source(node["title"], parent_title)
        if source_text and is_toc_like_source(source_text):
            source_text = ""
            matched = False
        scope = "legacy_resolver" if matched else "history_fallback"
    if not source_text:
        source_text = fallback_source_text(node)
        matched = False
        scope = "history_fallback"
    if not matched or scope == "history_fallback":
        fallback_items.append({"id": section_id, "title": node["title"], "source_text": source_text})
    item = {
        "id": section_id,
        "title": node["title"],
        "number": node.get("number"),
        "level": len(path),
        "required_status": status_for_title(node["title"], matched),
        "source_text": source_text,
        "children": [],
    }
    item["children"] = [
        convert_node(child, path + [index], resolve_source, fallback_items, node["title"], candidates_by_id, source_text)
        for index, child in enumerate(node["children"], start=1)
    ]
    return item


def add_review_item(review_items, message, source_text, section_id=None):
    review_items.append({
        "message": message,
        "source_text": source_text,
        "suggested_section_id": section_id,
        "required_status": CONFIRM,
    })


def candidate_has_parent_context(section_id, candidates_by_id):
    item = candidates_by_id.get(section_id) or {}
    return any(candidate.get("scope") == "parent_context" for candidate in item.get("candidates", []))


def collect_final_quality_review(sections, candidates_by_id):
    review_items = []

    def walk(items, parent=None):
        for section in items or []:
            source_text = section.get("source_text", "")
            section_id = section.get("id")
            if is_toc_like_source(source_text):
                add_review_item(review_items, "source_text 疑似来自目录页或末尾页码，需改用当前招标文件正文/表格候选。", source_text, section_id)
            if len(source_text) > 800:
                add_review_item(review_items, "source_text 过长，疑似整段 zone 文本，需改用具体 block/table 原文。", source_text, section_id)
            if parent and normalize(source_text) == normalize(parent.get("source_text", "")):
                add_review_item(review_items, "child 的 source_text 与父项完全相同，需复核是否误用了父项标题。", source_text, section_id)
            if parent and candidate_has_parent_context(section_id, candidates_by_id):
                chosen = candidates_by_id.get(section_id, {})
                final_scope = next((candidate.get("scope") for candidate in chosen.get("candidates", []) if normalize(candidate.get("source_text", "")) == normalize(source_text)), "")
                if final_scope in {"", "full_text"}:
                    add_review_item(review_items, "该 child 存在 parent_context 候选，但最终未使用父项上下文原文，需人工复核。", source_text, section_id)
            children = section.get("children", []) or []
            parent_text = normalize(source_text)
            counts = {}
            for child in children:
                child_text = normalize(child.get("source_text", ""))
                counts.setdefault(child_text, []).append(child)
            for child_text, same_text_children in counts.items():
                if child_text and child_text == parent_text and len(same_text_children) > 1:
                    for child in same_text_children:
                        add_review_item(review_items, "多个 sibling child 复用同一个父项 source_text，需复核是否误用了父项标题。", child.get("source_text", ""), child.get("id"))
            walk(children, section)

    walk(sections)
    return review_items


def build_context(history):
    return {
        "history_fallback_policy": {
            "summary": "当前招标文件无法可靠匹配逐字原文的历史目录项仍按历史经验保留，并将 required_status 标为待确认。",
            "source_text": history.get("outline_source", {}).get("source_text", ""),
        },
        "numbering_policy": {
            "summary": "number 字段继承历史商务标标题编号；历史无编号标题保持 null。",
            "source_text": history.get("outline_source", {}).get("source_text", ""),
        },
    }


def build_review_items(history, fallback_items):
    review_items = []
    if fallback_items:
        sample = "；".join(f"{item['id']} {item['title']}" for item in fallback_items[:20])
        add_review_item(review_items, f"部分历史经验目录项未匹配到当前招标文件逐字原文，已保留并标为待确认；请重点复核：{sample}", history.get("outline_source", {}).get("source_text", ""), None)

    supply_chain_source = ""
    for item in fallback_items:
        if item["title"].startswith("9.19"):
            supply_chain_source = item.get("source_text", "")
            break
    if supply_chain_source:
        add_review_item(review_items, "历史目录中 9.19 供应链协同相关子项可能属于具体项目素材库组装项，当前招标文件未见逐字提交要求，是否全部作为独立目录项需人工确认。", supply_chain_source, "sec-009")
    return review_items


def generate_outline(history_path=HISTORY_PATH, tender_path=TENDER_PATH, user_inputs_path=None, output_path=OUTLINE_PATH, candidates_path=CANDIDATES_PATH):
    history = load_json(history_path)
    tender = load_json(tender_path)
    candidates_by_id = load_candidates(candidates_path)

    roots = build_history_tree(history.get("outline_candidates", []))
    resolve_source = build_source_resolver(tender)
    fallback_items = []
    sections = [
        convert_node(node, [index], resolve_source, fallback_items, candidates_by_id=candidates_by_id)
        for index, node in enumerate(roots, start=1)
    ]

    review_items = build_review_items(history, fallback_items)
    review_items.extend(collect_final_quality_review(sections, candidates_by_id))

    outline = {
        "schema_version": "business_bid_outline.v1",
        "document_name": tender.get("document_name", ""),
        "outline_source": history.get("outline_source", {}),
        "context": build_context(history),
        "sections": sections,
        "review_items": review_items,
    }

    Path(output_path).write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    return outline


def main():
    outline = generate_outline()
    print(f"OK wrote {OUTLINE_PATH.name}: sections={len(outline['sections'])} review_items={len(outline['review_items'])}")


if __name__ == "__main__":
    main()
