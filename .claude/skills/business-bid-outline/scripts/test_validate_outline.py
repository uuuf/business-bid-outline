import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_outline.py")


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_outline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_outline():
    return {
        "schema_version": "business_bid_outline.v1",
        "document_name": "招标文件.docx",
        "outline_source": {
            "section_title": "历史商务标投标文件目录",
            "source_text": "商务评分索引表\n一、投标函",
            "confidence": "high",
            "source_type": "history_bid_toc",
        },
        "context": {},
        "sections": [
            {
                "id": "sec-001",
                "title": "商务评分索引表",
                "number": None,
                "level": 1,
                "required_status": "待确认",
                "source_text": "商务评分索引表",
                "children": [
                    {
                        "id": "sec-001-001",
                        "title": "评分索引明细",
                        "number": "1.1",
                        "level": 2,
                        "required_status": "待确认",
                        "source_text": "评分索引明细",
                        "children": [],
                    }
                ],
            }
        ],
        "review_items": [],
    }


class ValidateOutlineTest(unittest.TestCase):
    def test_accepts_number_string_or_null(self):
        validator = load_validator()
        self.assertEqual(validator.validate(valid_outline()), [])

    def test_rejects_missing_number(self):
        validator = load_validator()
        outline = valid_outline()
        del outline["sections"][0]["number"]
        errors = validator.validate(outline)
        self.assertIn("sections[0].number: missing required field", errors)

    def test_rejects_non_string_number(self):
        validator = load_validator()
        outline = copy.deepcopy(valid_outline())
        outline["sections"][0]["children"][0]["number"] = 1.1
        errors = validator.validate(outline)
        self.assertIn("sections[0].children[0].number: expected string or null", errors)


if __name__ == "__main__":
    unittest.main()
