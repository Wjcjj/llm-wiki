from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_wiki import (  # noqa: E402
    DuplicateSourceError,
    InMemorySourceStorage,
    InvalidSourceError,
    SourceNotFoundError,
    SourceRegistry,
)


class SourceRegistryTests(unittest.TestCase):
    def test_register_source_normalizes_id_and_fields(self) -> None:
        registry = SourceRegistry()

        source = registry.register_source(
            name=" OpenAI Docs ",
            kind="WEB",
            location=" https://platform.openai.com/docs ",
            tags=["Docs", "LLM", "docs", "  "],
        )

        self.assertEqual(source.id, "openai-docs")
        self.assertEqual(source.name, "OpenAI Docs")
        self.assertEqual(source.kind, "web")
        self.assertEqual(source.location, "https://platform.openai.com/docs")
        self.assertEqual(source.tags, ("docs", "llm"))
        self.assertTrue(source.enabled)
        self.assertIsNotNone(registry.get_source("OpenAI Docs"))

    def test_register_duplicate_source_id_is_rejected(self) -> None:
        registry = SourceRegistry()
        registry.register_source(name="Main Docs", kind="web", location="https://example.com")

        with self.assertRaises(DuplicateSourceError):
            registry.register_source(
                name="Main Docs",
                kind="web",
                location="https://example.org",
            )

    def test_invalid_source_is_rejected(self) -> None:
        registry = SourceRegistry()

        with self.assertRaises(InvalidSourceError):
            registry.register_source(name="Broken", kind="video", location="https://example.com")

    def test_list_sources_filters_by_kind_enabled_and_tag(self) -> None:
        registry = SourceRegistry()
        registry.register_source(
            name="Docs",
            kind="web",
            location="https://example.com/docs",
            tags=["official"],
        )
        registry.register_source(
            name="Internal Notes",
            kind="manual",
            location="notion://workspace/page",
            tags=["draft"],
            enabled=False,
        )
        registry.register_source(
            name="Releases",
            kind="feed",
            location="https://example.com/feed.xml",
            tags=["official"],
        )

        self.assertEqual(
            [source.id for source in registry.list_sources(kind="web")],
            ["docs"],
        )
        self.assertEqual(
            [source.id for source in registry.list_sources(enabled=False)],
            ["internal-notes"],
        )
        self.assertEqual(
            [source.id for source in registry.list_sources(tag="official")],
            ["docs", "releases"],
        )

    def test_update_source_validates_changes_and_refreshes_timestamp(self) -> None:
        registry = SourceRegistry()
        source = registry.register_source(
            name="Docs",
            kind="web",
            location="https://example.com/docs",
        )
        later = datetime(2030, 1, 1, tzinfo=timezone.utc)

        with patch("llm_wiki.models.utc_now", return_value=later):
            updated = registry.update_source(
                source.id,
                description="  Current source of truth  ",
                tags=["Primary", "primary"],
                enabled=False,
            )

        self.assertEqual(updated.description, "Current source of truth")
        self.assertEqual(updated.tags, ("primary",))
        self.assertFalse(updated.enabled)
        self.assertEqual(updated.created_at, source.created_at)
        self.assertEqual(updated.updated_at, later)

        with self.assertRaises(InvalidSourceError):
            registry.update_source(source.id, id="new-id")

    def test_remove_source_returns_deleted_record(self) -> None:
        registry = SourceRegistry()
        source = registry.register_source(name="Docs", kind="web", location="https://example.com")

        removed = registry.remove_source("docs")

        self.assertEqual(removed, source)
        self.assertFalse(registry.has_source("docs"))
        with self.assertRaises(SourceNotFoundError):
            registry.get_source("docs")

    def test_registry_loads_existing_records_from_storage(self) -> None:
        storage = InMemorySourceStorage()
        registry = SourceRegistry(storage)
        registry.register_source(name="Docs", kind="web", location="https://example.com")

        loaded_registry = SourceRegistry(storage)

        self.assertEqual(len(loaded_registry), 1)
        self.assertEqual(loaded_registry.get_source("docs").location, "https://example.com")


if __name__ == "__main__":
    unittest.main()
