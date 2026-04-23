"""Shared parser adapter utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
import re
import unicodedata

from llm_wiki.parser_models import (
    DocumentSection,
    NormalizedDocument,
    ParseError,
    make_child_id,
    make_document_id,
)


class ParserError(RuntimeError):
    """Raised internally for recoverable parser failures."""


@dataclass(frozen=True, slots=True)
class ParserConfig:
    """Configuration shared by all parser adapters."""

    max_file_size_bytes: int = 10 * 1024 * 1024
    repo_max_files: int = 10_000
    repo_skip_dirs: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".git",
                ".hg",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                ".svn",
                ".tox",
                ".venv",
                "__pycache__",
                "build",
                "dist",
                "node_modules",
                "target",
                "venv",
            }
        )
    )
    repo_skip_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                ".7z",
                ".a",
                ".bin",
                ".bmp",
                ".dll",
                ".exe",
                ".gif",
                ".ico",
                ".jar",
                ".jpeg",
                ".jpg",
                ".lock",
                ".mp3",
                ".mp4",
                ".pdf",
                ".png",
                ".pyc",
                ".pyo",
                ".so",
                ".sqlite",
                ".webp",
                ".zip",
            }
        )
    )


class BaseParserAdapter(Protocol):
    """Adapter contract for source-specific parsers."""

    source_type: str

    def supports(self, path: Path) -> bool:
        """Return whether this adapter can parse the path."""

    def parse(self, path: Path) -> NormalizedDocument:
        """Parse a path into a normalized document."""


_LANGUAGE_BY_EXTENSION = {
    ".bat": "batch",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".md": "markdown",
    ".ps1": "powershell",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "shell",
    ".sql": "sql",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".txt": "text",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def extension_language(path: Path) -> str | None:
    return _LANGUAGE_BY_EXTENSION.get(path.suffix.lower())


def resolve_source_path(path: Path) -> str:
    """Resolve paths when possible while still tolerating broken inputs."""

    try:
        return str(path.resolve())
    except (OSError, RuntimeError):
        return str(path)


def normalize_text(text: str) -> str:
    """Normalize unicode and remove low-signal whitespace."""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]

    collapsed: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            collapsed.append(line)
            continue
        blank_count += 1
        if blank_count <= 2:
            collapsed.append("")

    return "\n".join(collapsed).strip()


def infer_language(text: str) -> str:
    """Infer a coarse human language label without external dependencies."""

    if not text.strip():
        return "unknown"

    cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    if cjk_count >= 5:
        return "zh"

    letters = re.findall(r"[A-Za-z]", text)
    if len(letters) >= 20:
        return "en"

    return "unknown"


def title_from_text(path: Path, text: str) -> str:
    """Infer a useful title from content or filename."""

    for line in text.splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped[:120]
    return path.stem or path.name


def is_binary_bytes(sample: bytes) -> bool:
    """Detect obvious binary data from a small byte sample."""

    if not sample:
        return False
    if b"\x00" in sample:
        return True

    control_bytes = sum(1 for byte in sample if byte < 32 and byte not in b"\n\r\t\f\b")
    return control_bytes / len(sample) > 0.30


def ensure_readable_file(path: Path, config: ParserConfig) -> None:
    if not path.exists():
        raise ParserError(f"source does not exist: {path}")
    if not path.is_file():
        raise ParserError(f"source is not a file: {path}")
    if path.stat().st_size > config.max_file_size_bytes:
        raise ParserError(
            f"source is larger than max_file_size_bytes={config.max_file_size_bytes}"
        )


def read_text_file(path: Path, config: ParserConfig) -> str:
    """Read a text file with conservative encoding fallbacks."""

    ensure_readable_file(path, config)
    raw = path.read_bytes()
    if is_binary_bytes(raw[:4096]):
        raise ParserError(f"source appears to be binary: {path}")

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ParserError(f"source text encoding is not supported: {path}")


def basic_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "file_name": path.name,
        "suffix": path.suffix.lower(),
    }
    try:
        stat = path.stat()
    except OSError:
        return metadata

    metadata["size_bytes"] = stat.st_size
    metadata["modified_at"] = stat.st_mtime
    return metadata


def build_failure_document(
    path: Path,
    source_type: str,
    message: str,
    *,
    error_type: str = "ParseError",
    metadata: dict[str, object] | None = None,
) -> NormalizedDocument:
    source_path = resolve_source_path(path)
    doc_id = make_document_id(source_path, source_type)
    error = ParseError(
        message=message,
        error_type=error_type,
        source_path=source_path,
    )
    section = DocumentSection(
        section_id=make_child_id(doc_id, "section", 0, "failed"),
        heading=path.stem or path.name or "Unreadable source",
        level=1,
        content="",
        kind="text",
    )
    return NormalizedDocument(
        doc_id=doc_id,
        source_path=source_path,
        source_type=source_type,
        title=path.stem or path.name or "Unreadable source",
        language="unknown",
        metadata=dict(metadata or {}),
        sections=(section,),
        parse_quality="failed",
        errors=(error,),
    )
