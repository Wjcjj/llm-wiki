from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_wiki import JsonSourceStorage, SourceRegistry, SourceStorageError  # noqa: E402


class JsonSourceStorageTests(unittest.TestCase):
    def test_missing_registry_file_loads_as_empty(self) -> None:
        with TemporaryDirectory() as directory:
            storage = JsonSourceStorage(Path(directory) / "registry.json")

            self.assertEqual(storage.load_records(), {})

    def test_registry_round_trips_through_json_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sources" / "registry.json"
            registry = SourceRegistry(JsonSourceStorage(path))
            created = registry.register_source(
                name="OpenAI Docs",
                kind="web",
                location="https://platform.openai.com/docs",
                description="Official API documentation",
                tags=["official", "api"],
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            loaded_registry = SourceRegistry(JsonSourceStorage(path))
            loaded = loaded_registry.get_source(created.id)

            self.assertEqual(payload["version"], 1)
            self.assertIn("openai-docs", payload["sources"])
            self.assertEqual(loaded, created)

    def test_invalid_json_payload_raises_storage_error(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text("{not valid json", encoding="utf-8")
            storage = JsonSourceStorage(path)

            with self.assertRaises(SourceStorageError):
                storage.load_records()

    def test_mismatched_record_key_raises_storage_error(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sources": {
                            "docs": {
                                "id": "other-docs",
                                "name": "Docs",
                                "kind": "web",
                                "location": "https://example.com",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SourceStorageError):
                JsonSourceStorage(path).load_records()


if __name__ == "__main__":
    unittest.main()
