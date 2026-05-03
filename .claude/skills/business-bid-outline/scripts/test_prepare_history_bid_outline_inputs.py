import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


SCRIPT = Path(__file__).with_name("prepare_history_bid_outline_inputs.py")


DOCX_WRAPPERS = {
    "[Content_Types].xml": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>
</Types>""",
    "_rels/.rels": """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>""",
}


def paragraph(text, style=None):
    style_xml = ""
    if style:
        style_xml = f'<w:pPr><w:pStyle w:val="{escape(style)}"/></w:pPr>'
    return f"<w:p>{style_xml}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>"


def make_docx(path, paragraphs):
    document = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">
  <w:body>
    %s
  </w:body>
</w:document>""" % "\n".join(paragraphs)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in DOCX_WRAPPERS.items():
            archive.writestr(name, content)
        archive.writestr("word/document.xml", document)


class PrepareHistoryBidOutlineInputsTest(unittest.TestCase):
    def run_script(self, paragraphs):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            docx_path = tmpdir / "历史商务标投标文件.docx"
            output_path = tmpdir / "history_bid_outline_inputs.json"
            make_docx(docx_path, paragraphs)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(docx_path), "--output", str(output_path)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return json.loads(output_path.read_text(encoding="utf-8"))

    def test_extracts_outline_candidates_from_history_toc_page(self):
        output = self.run_script([
            paragraph("封面"),
            paragraph("目 录"),
            paragraph("一、投标函及授权文件\t1"),
            paragraph("（一）投标函\t2"),
            paragraph("（二）法定代表人授权委托书\t3"),
            paragraph("二、资格证明文件 4"),
            paragraph("1. 营业执照 5"),
            paragraph("三、商务偏差表 6"),
            paragraph("第一章 正文", "Heading1"),
        ])

        self.assertEqual(output["document_name"], "历史商务标投标文件.docx")
        self.assertEqual(output["outline_source"]["source_type"], "history_bid_toc")
        self.assertEqual(output["outline_source"]["history_document_name"], "历史商务标投标文件.docx")
        self.assertIn("一、投标函及授权文件\t1", output["outline_source"]["source_text"])

        candidates = output["outline_candidates"]
        self.assertEqual([candidate["title_hint"] for candidate in candidates], [
            "投标函及授权文件",
            "投标函",
            "法定代表人授权委托书",
            "资格证明文件",
            "营业执照",
            "商务偏差表",
        ])
        self.assertEqual([candidate["level"] for candidate in candidates], [1, 2, 2, 1, 2, 1])
        self.assertEqual(candidates[0]["source_text"], "一、投标函及授权文件\t1")
        self.assertEqual(candidates[0]["source_type"], "history_bid_toc")

    def test_falls_back_to_heading_structure_when_no_toc_exists(self):
        output = self.run_script([
            paragraph("投标函及授权文件", "Heading1"),
            paragraph("投标函", "Heading2"),
            paragraph("法定代表人授权委托书", "Heading2"),
            paragraph("资格证明文件", "Heading1"),
            paragraph("营业执照", "Heading2"),
        ])

        self.assertEqual(output["outline_source"]["source_type"], "history_bid_headings")
        self.assertEqual([candidate["title_hint"] for candidate in output["outline_candidates"]], [
            "投标函及授权文件",
            "投标函",
            "法定代表人授权委托书",
            "资格证明文件",
            "营业执照",
        ])
        self.assertEqual([candidate["level"] for candidate in output["outline_candidates"]], [1, 2, 2, 1, 2])
        self.assertEqual(output["outline_candidates"][1]["source_text"], "投标函")


if __name__ == "__main__":
    unittest.main()
