from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_wiki import DocumentParser, ParserConfig  # noqa: E402
from llm_wiki.parsers.document import DocxParserAdapter, MarkdownParserAdapter, PdfParserAdapter  # noqa: E402


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class DocumentParserTests(unittest.TestCase):
    def test_markdown_parser_preserves_headings_and_code_blocks(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "guide.md"
            path.write_text(
                "# Guide\n\nIntro text.\n\n## Example\n\n```python\nprint('hello')\n```\n",
                encoding="utf-8",
            )

            document = MarkdownParserAdapter().parse(path)

            self.assertEqual(document.source_type, "md")
            self.assertEqual(document.title, "Guide")
            self.assertEqual([section.heading for section in document.sections], ["Guide", "Example"])
            self.assertEqual(document.sections[0].kind, "markdown")
            self.assertEqual(len(document.code_blocks), 1)
            self.assertEqual(document.code_blocks[0].language, "python")
            self.assertIn("print('hello')", document.code_blocks[0].content)
            self.assertEqual(document.parse_quality, "high")

    def test_txt_parser_is_routed_by_document_parser(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("Project Notes\n\nThis is a local knowledge source.", encoding="utf-8")

            document = DocumentParser().parse_path(path)

            self.assertEqual(document.source_type, "txt")
            self.assertEqual(document.title, "Project Notes")
            self.assertEqual(document.sections[0].kind, "text")
            self.assertEqual(document.language, "en")

    def test_docx_parser_extracts_paragraphs_headings_and_tables(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.docx"
            self._write_docx(path)

            document = DocxParserAdapter().parse(path)

            self.assertEqual(document.source_type, "docx")
            self.assertEqual(document.title, "Docx Title")
            self.assertEqual(document.sections[0].heading, "Project Overview")
            self.assertIn("A paragraph from the document.", document.sections[0].content)
            self.assertTrue(any(section.kind == "table" for section in document.sections))
            self.assertEqual(document.parse_quality, "high")

    def test_pdf_parser_uses_optional_pypdf_when_available(self) -> None:
        class FakePage:
            def __init__(self, text: str) -> None:
                self.text = text

            def extract_text(self) -> str:
                return self.text

        class FakeReader:
            metadata = {"/Title": "PDF Title"}
            pages = [FakePage("First page text."), FakePage("Second page text.")]

            def __init__(self, _: str) -> None:
                pass

        with TemporaryDirectory() as directory:
            path = Path(directory) / "paper.pdf"
            path.write_bytes(b"%PDF-1.4 fake test payload")
            fake_pypdf = SimpleNamespace(PdfReader=FakeReader)

            with patch("llm_wiki.parsers.document.importlib.import_module", return_value=fake_pypdf):
                document = PdfParserAdapter().parse(path)

            self.assertEqual(document.source_type, "pdf")
            self.assertEqual(document.title, "PDF Title")
            self.assertEqual([section.heading for section in document.sections], ["Page 1", "Page 2"])
            self.assertEqual(document.parse_quality, "high")

    def test_pdf_parser_returns_structured_failure_without_pypdf(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "paper.pdf"
            path.write_bytes(b"%PDF-1.4 fake test payload")

            with patch(
                "llm_wiki.parsers.document.importlib.import_module",
                side_effect=ModuleNotFoundError("pypdf"),
            ):
                document = PdfParserAdapter().parse(path)

            self.assertEqual(document.source_type, "pdf")
            self.assertEqual(document.parse_quality, "failed")
            self.assertEqual(document.errors[0].error_type, "OptionalDependencyMissing")

    def test_parse_many_is_failure_isolated(self) -> None:
        with TemporaryDirectory() as directory:
            good = Path(directory) / "notes.txt"
            bad = Path(directory) / "archive.unknown"
            good.write_text("Useful notes", encoding="utf-8")
            bad.write_text(json.dumps({"not": "supported"}), encoding="utf-8")

            documents = DocumentParser().parse_many([good, bad])

            self.assertEqual(len(documents), 2)
            self.assertEqual(documents[0].parse_quality, "high")
            self.assertEqual(documents[1].parse_quality, "failed")
            self.assertEqual(documents[1].errors[0].error_type, "UnsupportedSourceType")

    def test_file_size_limit_returns_structured_failure(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "large.txt"
            path.write_text("too much", encoding="utf-8")
            parser = DocumentParser(config=ParserConfig(max_file_size_bytes=1))

            document = parser.parse_path(path)

            self.assertEqual(document.parse_quality, "failed")
            self.assertIn("max_file_size_bytes", document.errors[0].message)

    def _write_docx(self, path: Path) -> None:
        document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Project Overview</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>A paragraph from the document.</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Term</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Definition</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>
"""
        core_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties
  xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Docx Title</dc:title>
  <dc:creator>Unit Test</dc:creator>
</cp:coreProperties>
"""
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
            archive.writestr("docProps/core.xml", core_xml)


if __name__ == "__main__":
    unittest.main()
