"""Public parser router for Milestone 2."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from llm_wiki.parser_models import NormalizedDocument
from llm_wiki.parsers import (
    BaseParserAdapter,
    DocxParserAdapter,
    MarkdownParserAdapter,
    NotebookParserAdapter,
    ParserConfig,
    PdfParserAdapter,
    RepoParserAdapter,
    TxtParserAdapter,
)
from llm_wiki.parsers.base import build_failure_document


class DocumentParser:
    """Route supported paths to parser adapters and isolate failures."""

    def __init__(
        self,
        *,
        config: ParserConfig | None = None,
        adapters: Iterable[BaseParserAdapter] | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.adapters = tuple(adapters or self._default_adapters())

    def parse_path(self, path: str | Path) -> NormalizedDocument:
        """Parse one file or folder into a normalized document."""

        source_path = Path(path)
        adapter = self._adapter_for(source_path)
        if adapter is None:
            source_type = "folder" if source_path.is_dir() else source_path.suffix.lower().lstrip(".") or "unknown"
            return build_failure_document(
                source_path,
                source_type,
                f"unsupported source type for path: {source_path}",
                error_type="UnsupportedSourceType",
            )

        try:
            return adapter.parse(source_path)
        except Exception as exc:
            return build_failure_document(
                source_path,
                getattr(adapter, "source_type", "unknown"),
                str(exc),
                error_type=exc.__class__.__name__,
            )

    def parse_many(self, paths: Iterable[str | Path]) -> list[NormalizedDocument]:
        """Parse many paths while preserving input order and failure isolation."""

        return [self.parse_path(path) for path in paths]

    def _adapter_for(self, path: Path) -> BaseParserAdapter | None:
        for adapter in self.adapters:
            try:
                if adapter.supports(path):
                    return adapter
            except OSError:
                continue
        return None

    def _default_adapters(self) -> tuple[BaseParserAdapter, ...]:
        return (
            RepoParserAdapter(self.config),
            MarkdownParserAdapter(self.config),
            TxtParserAdapter(self.config),
            NotebookParserAdapter(self.config),
            DocxParserAdapter(self.config),
            PdfParserAdapter(self.config),
        )
