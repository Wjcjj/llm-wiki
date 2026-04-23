"""Repository and folder parser adapter."""

from __future__ import annotations

from pathlib import Path

from llm_wiki.parser_models import CodeBlock, DocumentSection, NormalizedDocument, ParseError
from llm_wiki.parser_models import make_child_id, make_document_id
from llm_wiki.parsers.base import (
    ParserConfig,
    basic_metadata,
    build_failure_document,
    extension_language,
    infer_language,
    is_binary_bytes,
    normalize_text,
    read_text_file,
    resolve_source_path,
)


class RepoParserAdapter:
    """Parse a local repository or folder into one normalized document."""

    source_type = "repo"
    documentation_extensions = frozenset({".md", ".markdown", ".mdown", ".mkd", ".rst", ".txt"})
    code_extensions = frozenset(
        {
            ".bat",
            ".c",
            ".cpp",
            ".cs",
            ".css",
            ".go",
            ".h",
            ".hpp",
            ".html",
            ".java",
            ".js",
            ".json",
            ".jsx",
            ".ps1",
            ".py",
            ".rb",
            ".rs",
            ".sh",
            ".sql",
            ".toml",
            ".ts",
            ".tsx",
            ".xml",
            ".yaml",
            ".yml",
        }
    )

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    def supports(self, path: Path) -> bool:
        return path.is_dir()

    def parse(self, path: Path) -> NormalizedDocument:
        if not path.exists() or not path.is_dir():
            return build_failure_document(path, self.source_type, f"source is not a folder: {path}")

        source_path = resolve_source_path(path)
        doc_id = make_document_id(source_path, self.source_type)
        sections: list[DocumentSection] = []
        code_blocks: list[CodeBlock] = []
        errors: list[ParseError] = []
        skipped_files: list[dict[str, object]] = []
        tree_lines: list[str] = []
        parsed_file_count = 0

        try:
            files = list(self._iter_files(path))
        except OSError as exc:
            return build_failure_document(
                path,
                self.source_type,
                str(exc),
                error_type=exc.__class__.__name__,
            )

        for file_index, file_path in enumerate(files):
            if file_index >= self.config.repo_max_files:
                errors.append(
                    ParseError(
                        message=f"repo file limit exceeded: {self.config.repo_max_files}",
                        error_type="RepoFileLimitExceeded",
                        source_path=source_path,
                    )
                )
                break

            relative_path = self._relative_path(path, file_path)
            tree_lines.append(relative_path)

            skip_reason = self._skip_reason(file_path)
            if skip_reason:
                skipped_files.append({"path": relative_path, "reason": skip_reason})
                continue

            if file_path.suffix.lower() in self.documentation_extensions:
                try:
                    content = normalize_text(read_text_file(file_path, self.config))
                except Exception as exc:
                    errors.append(
                        ParseError(
                            message=str(exc),
                            error_type=exc.__class__.__name__,
                            source_path=resolve_source_path(file_path),
                        )
                    )
                    continue
                if content:
                    sections.append(
                        DocumentSection(
                            section_id=make_child_id(
                                doc_id,
                                "section",
                                len(sections) + 1,
                                relative_path,
                            ),
                            heading=relative_path,
                            level=2,
                            content=content,
                            kind="markdown" if file_path.suffix.lower() in {".md", ".markdown", ".mdown", ".mkd"} else "text",
                        )
                    )
                    parsed_file_count += 1
                continue

            if file_path.suffix.lower() in self.code_extensions:
                try:
                    content = normalize_text(read_text_file(file_path, self.config))
                except Exception as exc:
                    errors.append(
                        ParseError(
                            message=str(exc),
                            error_type=exc.__class__.__name__,
                            source_path=resolve_source_path(file_path),
                        )
                    )
                    continue
                if content:
                    code_blocks.append(
                        CodeBlock(
                            block_id=make_child_id(
                                doc_id,
                                "code",
                                len(code_blocks),
                                relative_path,
                            ),
                            language=extension_language(file_path),
                            content=content,
                            source_path=relative_path,
                            metadata={"absolute_path": resolve_source_path(file_path)},
                        )
                    )
                    parsed_file_count += 1

        tree_section = DocumentSection(
            section_id=make_child_id(doc_id, "section", 0, "tree"),
            heading="Repository tree",
            level=1,
            content="\n".join(tree_lines),
            kind="text",
        )
        sections.insert(0, tree_section)

        metadata = basic_metadata(path)
        metadata.update(
            {
                "file_count": len(files),
                "parsed_file_count": parsed_file_count,
                "skipped_files": skipped_files,
            }
        )
        visible_text = "\n\n".join(section.content for section in sections)
        parse_quality = "high" if parsed_file_count and not errors else "medium" if parsed_file_count else "low"
        return NormalizedDocument(
            doc_id=doc_id,
            source_path=source_path,
            source_type=self.source_type,
            title=path.name or "Repository",
            language=infer_language(visible_text),
            metadata=metadata,
            sections=tuple(sections),
            code_blocks=tuple(code_blocks),
            parse_quality=parse_quality,
            errors=tuple(errors),
        )

    def _iter_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                if child.name in self.config.repo_skip_dirs or child.name.startswith("."):
                    continue
                files.extend(self._iter_files(child))
            elif child.is_file():
                files.append(child)
        return files

    def _skip_reason(self, path: Path) -> str | None:
        suffix = path.suffix.lower()
        if suffix in self.config.repo_skip_extensions:
            return "skipped_extension"

        try:
            if path.stat().st_size > self.config.max_file_size_bytes:
                return "file_too_large"
            with path.open("rb") as handle:
                if is_binary_bytes(handle.read(4096)):
                    return "binary_file"
        except OSError as exc:
            return f"unreadable:{exc.__class__.__name__}"

        if suffix not in self.documentation_extensions and suffix not in self.code_extensions:
            return "unsupported_extension"

        return None

    def _relative_path(self, root: Path, path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.name
