"""Normalized parser output models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import uuid


SECTION_KINDS = frozenset({"code", "list", "markdown", "quote", "table", "text"})
PARSE_QUALITY_LEVELS = frozenset({"failed", "high", "low", "medium"})


def make_document_id(source_path: str | Path, source_type: str) -> str:
    """Create a deterministic UUID for a parsed source."""

    raw_path = str(source_path)
    try:
        raw_path = str(Path(source_path).resolve())
    except (OSError, RuntimeError):
        pass

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"llm-wiki:{source_type}:{raw_path}"))


def make_child_id(doc_id: str, kind: str, index: int, label: str = "") -> str:
    """Create a deterministic child ID scoped to a document."""

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc_id}:{kind}:{index}:{label}"))


@dataclass(frozen=True, slots=True)
class ParseError:
    """Structured parser error that can travel downstream."""

    message: str
    error_type: str = "ParseError"
    source_path: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "error_type": self.error_type,
            "source_path": self.source_path,
            "context": dict(self.context),
        }


@dataclass(frozen=True, slots=True)
class DocumentSection:
    """A normalized content section in reading order."""

    section_id: str
    heading: str
    level: int
    content: str
    kind: str = "text"

    def __post_init__(self) -> None:
        if not self.section_id.strip():
            raise ValueError("section_id cannot be empty")
        if not self.heading.strip():
            raise ValueError("heading cannot be empty")
        if self.level < 1:
            raise ValueError("section level must be >= 1")
        if self.kind not in SECTION_KINDS:
            allowed = ", ".join(sorted(SECTION_KINDS))
            raise ValueError(f"section kind must be one of: {allowed}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "heading": self.heading,
            "level": self.level,
            "content": self.content,
            "kind": self.kind,
        }


@dataclass(frozen=True, slots=True)
class CodeBlock:
    """A normalized code block extracted from a source."""

    block_id: str
    content: str
    language: str | None = None
    source_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "language": self.language,
            "content": self.content,
            "source_path": self.source_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AssetReference:
    """A non-text asset discovered during parsing."""

    asset_id: str
    source_path: str
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "source_path": self.source_path,
            "kind": self.kind,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    """Stable parser output consumed by downstream wiki stages."""

    doc_id: str
    source_path: str
    source_type: str
    title: str
    language: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: tuple[DocumentSection, ...] = ()
    code_blocks: tuple[CodeBlock, ...] = ()
    assets: tuple[AssetReference, ...] = ()
    parse_quality: str = "high"
    errors: tuple[ParseError, ...] = ()

    def __post_init__(self) -> None:
        if not self.doc_id.strip():
            raise ValueError("doc_id cannot be empty")
        if not self.source_path.strip():
            raise ValueError("source_path cannot be empty")
        if not self.source_type.strip():
            raise ValueError("source_type cannot be empty")
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if self.parse_quality not in PARSE_QUALITY_LEVELS:
            allowed = ", ".join(sorted(PARSE_QUALITY_LEVELS))
            raise ValueError(f"parse_quality must be one of: {allowed}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "title": self.title,
            "language": self.language,
            "metadata": dict(self.metadata),
            "sections": [section.to_dict() for section in self.sections],
            "code_blocks": [block.to_dict() for block in self.code_blocks],
            "assets": [asset.to_dict() for asset in self.assets],
            "parse_quality": self.parse_quality,
            "errors": [error.to_dict() for error in self.errors],
        }
