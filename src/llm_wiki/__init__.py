"""Core package for llm-wiki."""

from .models import SOURCE_KINDS, SourceRecord, normalize_source_id, normalize_tags
from .parser import DocumentParser
from .parser_models import (
    AssetReference,
    CodeBlock,
    DocumentSection,
    NormalizedDocument,
    PARSE_QUALITY_LEVELS,
    ParseError,
    SECTION_KINDS,
)
from .parsers import ParserConfig, ParserError
from .registry import (
    DuplicateSourceError,
    InvalidSourceError,
    RegistryError,
    SourceNotFoundError,
    SourceRegistry,
)
from .storage import InMemorySourceStorage, JsonSourceStorage, SourceStorageError

__all__ = [
    "SOURCE_KINDS",
    "DuplicateSourceError",
    "AssetReference",
    "CodeBlock",
    "DocumentParser",
    "DocumentSection",
    "InMemorySourceStorage",
    "InvalidSourceError",
    "JsonSourceStorage",
    "NormalizedDocument",
    "PARSE_QUALITY_LEVELS",
    "ParserConfig",
    "ParserError",
    "ParseError",
    "RegistryError",
    "SECTION_KINDS",
    "SourceNotFoundError",
    "SourceRecord",
    "SourceRegistry",
    "SourceStorageError",
    "normalize_source_id",
    "normalize_tags",
]
