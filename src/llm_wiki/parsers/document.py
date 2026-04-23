"""Document parser adapters."""

from __future__ import annotations

from pathlib import Path
import importlib
import re
import zipfile
from xml.etree import ElementTree

from llm_wiki.parser_models import CodeBlock, DocumentSection, NormalizedDocument, ParseError
from llm_wiki.parser_models import make_child_id, make_document_id
from llm_wiki.parsers.base import (
    ParserConfig,
    ParserError,
    basic_metadata,
    build_failure_document,
    ensure_readable_file,
    extension_language,
    infer_language,
    normalize_text,
    read_text_file,
    resolve_source_path,
    title_from_text,
)


class TxtParserAdapter:
    """Parse plain text files into a single text section."""

    source_type = "txt"

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".txt"

    def parse(self, path: Path) -> NormalizedDocument:
        try:
            raw = read_text_file(path, self.config)
            text = normalize_text(raw)
        except (OSError, ParserError) as exc:
            return build_failure_document(path, self.source_type, str(exc))

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)
        title = title_from_text(path, text)
        section = DocumentSection(
            section_id=make_child_id(doc_id, "section", 0, title),
            heading=title,
            level=1,
            content=text,
            kind="text",
        )
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=title,
            language=infer_language(text),
            metadata=basic_metadata(path),
            sections=(section,),
            parse_quality="high",
        )


class MarkdownParserAdapter:
    """Parse Markdown headings and fenced code blocks."""

    source_type = "md"
    extensions = frozenset({".markdown", ".md", ".mdown", ".mkd"})
    _heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
    _fence_pattern = re.compile(r"^(```|~~~)\s*([A-Za-z0-9_+.#-]*)?.*$")

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self.extensions

    def parse(self, path: Path) -> NormalizedDocument:
        try:
            raw = read_text_file(path, self.config)
        except (OSError, ParserError) as exc:
            return build_failure_document(path, self.source_type, str(exc))

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)
        sections: list[DocumentSection] = []
        code_blocks: list[CodeBlock] = []
        errors: list[ParseError] = []

        current_heading = path.stem or path.name
        current_level = 1
        current_lines: list[str] = []
        in_code_fence = False
        fence_marker = ""
        fence_language: str | None = None
        fence_start_line: int | None = None
        fence_lines: list[str] = []

        def flush_section() -> None:
            content = normalize_text("\n".join(current_lines))
            if not content and (sections or current_heading == (path.stem or path.name)):
                return
            index = len(sections)
            sections.append(
                DocumentSection(
                    section_id=make_child_id(doc_id, "section", index, current_heading),
                    heading=current_heading,
                    level=current_level,
                    content=content,
                    kind="markdown",
                )
            )

        for line_number, line in enumerate(raw.splitlines(), start=1):
            fence_match = self._fence_pattern.match(line)
            if in_code_fence:
                if fence_match and fence_match.group(1) == fence_marker:
                    content = "\n".join(fence_lines).rstrip()
                    block_index = len(code_blocks)
                    code_blocks.append(
                        CodeBlock(
                            block_id=make_child_id(
                                doc_id,
                                "code",
                                block_index,
                                f"{fence_language or ''}:{fence_start_line}",
                            ),
                            language=fence_language,
                            content=content,
                            source_path=source_path,
                            start_line=fence_start_line,
                            end_line=line_number,
                        )
                    )
                    current_lines.append(line)
                    in_code_fence = False
                    fence_marker = ""
                    fence_language = None
                    fence_start_line = None
                    fence_lines = []
                    continue

                fence_lines.append(line)
                current_lines.append(line)
                continue

            if fence_match:
                in_code_fence = True
                fence_marker = fence_match.group(1)
                fence_language = fence_match.group(2) or None
                fence_start_line = line_number
                fence_lines = []
                current_lines.append(line)
                continue

            heading_match = self._heading_pattern.match(line)
            if heading_match:
                flush_section()
                current_heading = heading_match.group(2).strip()
                current_level = len(heading_match.group(1))
                current_lines = []
                continue

            current_lines.append(line)

        if in_code_fence:
            errors.append(
                ParseError(
                    message="markdown code fence was not closed",
                    error_type="UnclosedCodeFence",
                    source_path=source_path,
                    context={"start_line": fence_start_line},
                )
            )
            if fence_lines:
                code_blocks.append(
                    CodeBlock(
                        block_id=make_child_id(
                            doc_id,
                            "code",
                            len(code_blocks),
                            f"{fence_language or ''}:{fence_start_line}",
                        ),
                        language=fence_language,
                        content="\n".join(fence_lines).rstrip(),
                        source_path=source_path,
                        start_line=fence_start_line,
                        end_line=len(raw.splitlines()),
                    )
                )

        flush_section()
        all_text = normalize_text(raw)
        title = sections[0].heading if sections else title_from_text(path, all_text)
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=title,
            language=infer_language(all_text),
            metadata=basic_metadata(path),
            sections=tuple(sections),
            code_blocks=tuple(code_blocks),
            parse_quality="medium" if errors else "high",
            errors=tuple(errors),
        )


class DocxParserAdapter:
    """Parse DOCX files using the zipped Office XML structure."""

    source_type = "docx"
    _word_namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    _dc_namespace = "{http://purl.org/dc/elements/1.1/}"

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".docx"

    def parse(self, path: Path) -> NormalizedDocument:
        try:
            ensure_readable_file(path, self.config)
            with zipfile.ZipFile(path) as archive:
                document_xml = archive.read("word/document.xml")
                core_properties = self._read_core_properties(archive)
        except (KeyError, OSError, ParserError, zipfile.BadZipFile) as exc:
            return build_failure_document(path, self.source_type, str(exc))

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)

        try:
            root = ElementTree.fromstring(document_xml)
        except ElementTree.ParseError as exc:
            return build_failure_document(path, self.source_type, str(exc), error_type="XmlError")

        body = root.find(f".//{self._word_namespace}body")
        sections: list[DocumentSection] = []
        current_heading = core_properties.get("title") or path.stem or path.name
        current_level = 1
        current_lines: list[str] = []

        def flush_text_section() -> None:
            content = normalize_text("\n".join(current_lines))
            if not content and (sections or current_heading == (core_properties.get("title") or path.stem or path.name)):
                return
            sections.append(
                DocumentSection(
                    section_id=make_child_id(doc_id, "section", len(sections), current_heading),
                    heading=current_heading,
                    level=current_level,
                    content=content,
                    kind="text",
                )
            )

        if body is not None:
            for child in list(body):
                local_name = child.tag.rsplit("}", maxsplit=1)[-1]
                if local_name == "p":
                    text = normalize_text(self._paragraph_text(child))
                    if not text:
                        continue
                    heading_level = self._heading_level(child)
                    if heading_level is not None:
                        flush_text_section()
                        current_heading = text
                        current_level = heading_level
                        current_lines = []
                    else:
                        current_lines.append(text)
                elif local_name == "tbl":
                    table_text = normalize_text(self._table_text(child))
                    if table_text:
                        flush_text_section()
                        sections.append(
                            DocumentSection(
                                section_id=make_child_id(
                                    doc_id,
                                    "section",
                                    len(sections),
                                    "table",
                                ),
                                heading="Table",
                                level=max(current_level + 1, 2),
                                content=table_text,
                                kind="table",
                            )
                        )
                        current_lines = []

        flush_text_section()
        all_text = "\n\n".join(section.content for section in sections)
        title = core_properties.get("title") or self._first_heading(sections) or path.stem
        metadata = basic_metadata(path)
        metadata.update(core_properties)
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=title,
            language=infer_language(all_text),
            metadata=metadata,
            sections=tuple(sections),
            parse_quality="high" if all_text.strip() else "low",
        )

    def _read_core_properties(self, archive: zipfile.ZipFile) -> dict[str, str]:
        try:
            raw = archive.read("docProps/core.xml")
        except KeyError:
            return {}

        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            return {}

        properties: dict[str, str] = {}
        for key in ("title", "creator", "description", "subject"):
            element = root.find(f".//{self._dc_namespace}{key}")
            if element is not None and element.text and element.text.strip():
                properties[key] = element.text.strip()
        return properties

    def _paragraph_text(self, paragraph: ElementTree.Element) -> str:
        pieces: list[str] = []
        for element in paragraph.iter():
            local_name = element.tag.rsplit("}", maxsplit=1)[-1]
            if local_name == "t" and element.text:
                pieces.append(element.text)
            elif local_name == "tab":
                pieces.append("\t")
            elif local_name in {"br", "cr"}:
                pieces.append("\n")
        return "".join(pieces)

    def _table_text(self, table: ElementTree.Element) -> str:
        rows: list[str] = []
        for row in table.findall(f".//{self._word_namespace}tr"):
            cells: list[str] = []
            for cell in row.findall(f"./{self._word_namespace}tc"):
                cell_text = normalize_text(
                    " ".join(
                        self._paragraph_text(paragraph)
                        for paragraph in cell.findall(f".//{self._word_namespace}p")
                    )
                )
                cells.append(cell_text)
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)

    def _heading_level(self, paragraph: ElementTree.Element) -> int | None:
        style = paragraph.find(f"./{self._word_namespace}pPr/{self._word_namespace}pStyle")
        if style is None:
            return None

        style_value = style.attrib.get(f"{self._word_namespace}val", "")
        match = re.search(r"heading\s*([1-6])|Heading([1-6])", style_value, re.IGNORECASE)
        if match:
            return int(next(value for value in match.groups() if value))
        return None

    def _first_heading(self, sections: list[DocumentSection]) -> str | None:
        for section in sections:
            if section.heading and section.heading != "Table":
                return section.heading
        return None


class PdfParserAdapter:
    """Parse PDFs with optional pypdf support."""

    source_type = "pdf"

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".pdf"

    def parse(self, path: Path) -> NormalizedDocument:
        try:
            ensure_readable_file(path, self.config)
        except (OSError, ParserError) as exc:
            return build_failure_document(path, self.source_type, str(exc))

        try:
            pypdf = importlib.import_module("pypdf")
        except ModuleNotFoundError:
            return build_failure_document(
                path,
                self.source_type,
                "PDF parsing requires optional dependency 'pypdf'",
                error_type="OptionalDependencyMissing",
                metadata=basic_metadata(path),
            )

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)
        sections: list[DocumentSection] = []
        errors: list[ParseError] = []

        try:
            reader = pypdf.PdfReader(str(path))
        except Exception as exc:  # pypdf raises several format-specific exceptions.
            return build_failure_document(
                path,
                self.source_type,
                str(exc),
                error_type=exc.__class__.__name__,
                metadata=basic_metadata(path),
            )

        metadata = basic_metadata(path)
        raw_metadata = getattr(reader, "metadata", None)
        title = path.stem or path.name
        if raw_metadata:
            for key, value in dict(raw_metadata).items():
                clean_key = str(key).lstrip("/")
                metadata[f"pdf_{clean_key}"] = str(value)
                if clean_key.lower() == "title" and str(value).strip():
                    title = str(value).strip()

        pages = list(getattr(reader, "pages", []))
        for page_index, page in enumerate(pages, start=1):
            try:
                page_text = normalize_text(page.extract_text() or "")
            except Exception as exc:
                errors.append(
                    ParseError(
                        message=str(exc),
                        error_type=exc.__class__.__name__,
                        source_path=source_path,
                        context={"page": page_index},
                    )
                )
                continue

            if not page_text:
                continue

            sections.append(
                DocumentSection(
                    section_id=make_child_id(doc_id, "section", page_index - 1, f"page-{page_index}"),
                    heading=f"Page {page_index}",
                    level=1,
                    content=page_text,
                    kind="text",
                )
            )

        all_text = "\n\n".join(section.content for section in sections)
        parse_quality = "high" if sections and not errors else "medium" if sections else "low"
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=title,
            language=infer_language(all_text),
            metadata=metadata,
            sections=tuple(sections),
            parse_quality=parse_quality,
            errors=tuple(errors),
        )


def generic_text_section(path: Path, source_type: str, content: str) -> DocumentSection:
    """Build a reusable text section for repo parsing."""

    source_path = resolve_source_path(path)
    doc_id = make_document_id(source_path, source_type)
    title = title_from_text(path, content)
    return DocumentSection(
        section_id=make_child_id(doc_id, "section", 0, title),
        heading=title,
        level=1,
        content=normalize_text(content),
        kind="text",
    )


def language_for_code_path(path: Path) -> str | None:
    return extension_language(path)
