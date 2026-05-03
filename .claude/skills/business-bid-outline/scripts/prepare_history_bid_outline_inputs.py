import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
MAX_SOURCE_BLOCKS = 80


def qn(name):
    prefix, local = name.split(":", 1)
    return f"{{{NS[prefix]}}}{local}"


def text_from_element(element):
    parts = []
    for node in element.iter():
        if node.tag == qn("w:t") and node.text:
            parts.append(node.text)
        elif node.tag == qn("w:tab"):
            parts.append("\t")
        elif node.tag in {qn("w:br"), qn("w:cr")}:
            parts.append("\n")
    return "".join(parts).strip()


def paragraph_style(paragraph):
    p_style = paragraph.find("w:pPr/w:pStyle", NS)
    if p_style is None:
        return ""
    return p_style.attrib.get(qn("w:val"), "")


def compact_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize(text):
    return re.sub(r"\s+", "", text or "").lower()


def parse_docx(path):
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    body = root.find("w:body", NS)
    if body is None:
        return []
    return list(body)


def heading_level(text, style):
    style_text = style.lower()
    match = re.search(r"heading\s*([1-6])", style_text)
    if match:
        return int(match.group(1))
    match = re.search(r"标题\s*([1-6])", style)
    if match:
        return int(match.group(1))
    stripped = compact_text(text)
    patterns = [
        (1, r"^第[一二三四五六七八九十百]+[章节篇卷]\b"),
        (1, r"^[一二三四五六七八九十]+[、．.]\s*\S+"),
        (2, r"^[（(][一二三四五六七八九十]+[）)]\s*\S+"),
        (2, r"^\d+[、．.]\s*\S+"),
        (3, r"^\d+\.\d+\s*\S+"),
    ]
    for level, pattern in patterns:
        if re.match(pattern, stripped):
            return level
    return None


def update_heading_path(path, level, title):
    next_path = path[:]
    while len(next_path) >= level:
        next_path.pop()
    next_path.append(title)
    return next_path


def build_blocks(docx_path):
    blocks = []
    heading_path = []
    paragraph_index = 0
    for element in parse_docx(docx_path):
        if element.tag != qn("w:p"):
            continue
        paragraph_index += 1
        text = text_from_element(element)
        if not text:
            continue
        style = paragraph_style(element)
        level = heading_level(text, style)
        if level:
            heading_path = update_heading_path(heading_path, level, text)
        block = {
            "block_id": f"hb-{len(blocks) + 1:04d}",
            "type": "paragraph",
            "text": text,
            "paragraph_index": paragraph_index,
            "heading_path": heading_path[:],
        }
        if style:
            block["style"] = style
        if level:
            block["heading_level"] = level
        blocks.append(block)
    return blocks


def is_toc_title(text):
    return normalize(text) in {"目录", "目次", "contents"}


def is_toc_line(text):
    stripped = compact_text(text)
    if not stripped or len(stripped) > 140:
        return False
    if re.search(r"\t\s*\d+\s*$", stripped):
        return True
    if re.search(r"\s+\d+\s*$", stripped) and re.search(r"(附件|[一二三四五六七八九十]+[、．.]|[（(][一二三四五六七八九十]+[）)]|\d+[、．.]|\d+\.\d+)", stripped):
        return True
    return False


def find_toc_blocks(blocks):
    for index, block in enumerate(blocks):
        if not is_toc_title(block.get("text", "")):
            continue
        candidates = []
        for next_block in blocks[index + 1:index + 1 + MAX_SOURCE_BLOCKS]:
            text = next_block.get("text", "")
            if is_toc_line(text):
                candidates.append(next_block)
                continue
            if candidates and next_block.get("heading_level") == 1:
                break
            if len(candidates) >= 2 and not is_toc_line(text):
                break
        if candidates:
            return candidates
    return []


def strip_page_number(text):
    return re.sub(r"(?:\t|\s+)\d+\s*$", "", compact_text(text)).strip()


def infer_toc_level(text):
    stripped = strip_page_number(text)
    if re.match(r"^[一二三四五六七八九十]+[、．.]", stripped):
        return 1
    if re.match(r"^附件\s*\d+[A-Z]?(?:[-－]?\d+)?", stripped):
        return 1
    if re.match(r"^[（(][一二三四五六七八九十]+[）)]", stripped):
        return 2
    if re.match(r"^\d+\.\d+", stripped):
        return 3
    if re.match(r"^\d+[、．.]", stripped):
        return 2
    return 2


def title_from_toc_line(text):
    title = strip_page_number(text)
    replacements = [
        r"^[一二三四五六七八九十]+[、．.]\s*",
        r"^[（(][一二三四五六七八九十]+[）)]\s*",
        r"^\d+(?:\.\d+)?[、．.]\s*",
        r"^附件\s*\d+[A-Z]?(?:[-－]?\d+)?\s*",
    ]
    for pattern in replacements:
        title = re.sub(pattern, "", title)
    return title.strip() or strip_page_number(text)


def title_from_heading(text):
    title = compact_text(text)
    replacements = [
        r"^第[一二三四五六七八九十百]+[章节篇卷]\s*",
        r"^[一二三四五六七八九十]+[、．.]\s*",
        r"^[（(][一二三四五六七八九十]+[）)]\s*",
        r"^\d+(?:\.\d+)?[、．.]\s*",
    ]
    for pattern in replacements:
        title = re.sub(pattern, "", title)
    return title.strip() or compact_text(text)


def candidate_from_block(block, index, source_type, title_hint, level):
    return {
        "candidate_id": f"hist-cand-{index:03d}",
        "title_hint": title_hint,
        "level": level,
        "source_text": block.get("text", ""),
        "source_type": source_type,
        "block_id": block.get("block_id"),
        "heading_path": block.get("heading_path", []),
    }


def candidates_from_toc(toc_blocks):
    candidates = []
    for index, block in enumerate(toc_blocks, start=1):
        candidates.append(candidate_from_block(
            block,
            index,
            "history_bid_toc",
            title_from_toc_line(block.get("text", "")),
            infer_toc_level(block.get("text", "")),
        ))
    return candidates


def candidates_from_headings(blocks):
    heading_blocks = [block for block in blocks if block.get("heading_level")]
    if not heading_blocks:
        return []
    min_level = min(block.get("heading_level") for block in heading_blocks)
    candidates = []
    for index, block in enumerate(heading_blocks, start=1):
        level = max(1, block.get("heading_level") - min_level + 1)
        candidates.append(candidate_from_block(
            block,
            index,
            "history_bid_headings",
            title_from_heading(block.get("text", "")),
            level,
        ))
    return candidates


def make_outline_source(document_name, source_type, source_blocks, candidates):
    if source_blocks:
        source_text = "\n".join(block.get("text", "") for block in source_blocks)
    else:
        source_text = ""
    return {
        "section_title": "历史商务标投标文件目录" if source_type == "history_bid_toc" else "历史商务标投标文件标题结构",
        "source_text": source_text,
        "confidence": "high" if source_type == "history_bid_toc" else ("medium" if candidates else "low"),
        "source_type": source_type,
        "history_document_name": document_name,
    }


def build_output(docx_path):
    blocks = build_blocks(docx_path)
    toc_blocks = find_toc_blocks(blocks)
    if toc_blocks:
        source_type = "history_bid_toc"
        source_blocks = toc_blocks
        candidates = candidates_from_toc(toc_blocks)
    else:
        source_type = "history_bid_headings"
        candidates = candidates_from_headings(blocks)
        source_blocks = [block for block in blocks if block.get("heading_level")]
        if not candidates:
            source_type = "history_bid_unknown"
            source_blocks = []
    return {
        "document_name": docx_path.name,
        "blocks": blocks,
        "outline_source": make_outline_source(docx_path.name, source_type, source_blocks, candidates),
        "outline_candidates": candidates,
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare historical business bid outline candidates from a DOCX file.")
    parser.add_argument("docx", help="Historical business bid .docx file")
    parser.add_argument("--output", default="history_bid_outline_inputs.json", help="Output JSON path")
    args = parser.parse_args()

    docx_path = Path(args.docx)
    if not docx_path.exists():
        print(f"ERROR: file not found: {docx_path}", file=sys.stderr)
        return 2
    output = build_output(docx_path)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: wrote {args.output} with {len(output['outline_candidates'])} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
