"""Jupyter notebook parser adapter."""

from __future__ import annotations

import json
from pathlib import Path

from llm_wiki.parser_models import CodeBlock, DocumentSection, NormalizedDocument, ParseError
from llm_wiki.parser_models import make_child_id, make_document_id
from llm_wiki.parsers.base import (
    ParserConfig,
    ParserError,
    basic_metadata,
    build_failure_document,
    ensure_readable_file,
    infer_language,
    normalize_text,
    resolve_source_path,
    title_from_text,
)


class NotebookParserAdapter:
    """Parse .ipynb files without executing notebook code."""

    source_type = "ipynb"

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".ipynb"

    def parse(self, path: Path) -> NormalizedDocument:
        try:
            ensure_readable_file(path, self.config)
            notebook = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ParserError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return build_failure_document(path, self.source_type, str(exc))

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)
        metadata = basic_metadata(path)
        notebook_metadata = notebook.get("metadata", {})
        if isinstance(notebook_metadata, dict):
            metadata["notebook_metadata"] = notebook_metadata

        language = self._kernel_language(notebook_metadata)
        sections: list[DocumentSection] = []
        code_blocks: list[CodeBlock] = []
        errors: list[ParseError] = []
        markdown_text_parts: list[str] = []

        cells = notebook.get("cells", [])
        if not isinstance(cells, list):
            errors.append(
                ParseError(
                    message="notebook cells field is not a list",
                    error_type="InvalidNotebook",
                    source_path=source_path,
                )
            )
            cells = []

        for cell_index, cell in enumerate(cells):
            if not isinstance(cell, dict):
                errors.append(
                    ParseError(
                        message="notebook cell is not an object",
                        error_type="InvalidNotebookCell",
                        source_path=source_path,
                        context={"cell_index": cell_index},
                    )
                )
                continue

            cell_type = cell.get("cell_type")
            source = normalize_text(self._source_text(cell.get("source", "")))
            if cell_type == "markdown":
                heading, level = self._markdown_heading(path, source)
                sections.append(
                    DocumentSection(
                        section_id=make_child_id(doc_id, "section", len(sections), heading),
                        heading=heading,
                        level=level,
                        content=source,
                        kind="markdown",
                    )
                )
                markdown_text_parts.append(source)
            elif cell_type == "code":
                block_index = len(code_blocks)
                code_blocks.append(
                    CodeBlock(
                        block_id=make_child_id(doc_id, "code", block_index, str(cell_index)),
                        language=language if language != "unknown" else None,
                        content=source,
                        source_path=source_path,
                        metadata={
                            "cell_index": cell_index,
                            "execution_count": cell.get("execution_count"),
                        },
                    )
                )
                sections.append(
                    DocumentSection(
                        section_id=make_child_id(doc_id, "section", len(sections), f"code-{cell_index}"),
                        heading=f"Code cell {cell_index + 1}",
                        level=2,
                        content=source,
                        kind="code",
                    )
                )
            else:
                errors.append(
                    ParseError(
                        message=f"unsupported notebook cell type: {cell_type!r}",
                        error_type="UnsupportedNotebookCell",
                        source_path=source_path,
                        context={"cell_index": cell_index},
                    )
                )

        title = self._title_from_notebook(path, sections, markdown_text_parts)
        parse_quality = "high" if not errors else "medium" if sections or code_blocks else "failed"
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=title,
            language=language if language != "unknown" else infer_language("\n".join(markdown_text_parts)),
            metadata=metadata,
            sections=tuple(sections),
            code_blocks=tuple(code_blocks),
            parse_quality=parse_quality,
            errors=tuple(errors),
        )

    def _source_text(self, source: object) -> str:
        if isinstance(source, list):
            return "".join(str(part) for part in source)
        if isinstance(source, str):
            return source
        return str(source)

    def _kernel_language(self, metadata: object) -> str:
        if not isinstance(metadata, dict):
            return "unknown"

        language_info = metadata.get("language_info")
        if isinstance(language_info, dict) and isinstance(language_info.get("name"), str):
            return language_info["name"].strip().lower() or "unknown"

        kernelspec = metadata.get("kernelspec")
        if isinstance(kernelspec, dict) and isinstance(kernelspec.get("language"), str):
            return kernelspec["language"].strip().lower() or "unknown"

        return "unknown"

    def _markdown_heading(self, path: Path, source: str) -> tuple[str, int]:
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                hashes = len(stripped) - len(stripped.lstrip("#"))
                heading = stripped[hashes:].strip()
                if heading:
                    return heading, min(max(hashes, 1), 6)
        return title_from_text(path, source), 1

    def _title_from_notebook(
        self,
        path: Path,
        sections: list[DocumentSection],
        markdown_text_parts: list[str],
    ) -> str:
        for section in sections:
            if section.kind == "markdown" and section.heading:
                return section.heading
        return title_from_text(path, "\n".join(markdown_text_parts))
