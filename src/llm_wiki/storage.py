"""Storage adapters for source registry records."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Mapping, Protocol

from .models import SourceRecord, normalize_source_id


class SourceStorageError(RuntimeError):
    """Raised when registry persistence fails."""


class SourceStorage(Protocol):
    """Repository contract used by the source registry service."""

    def load_records(self) -> dict[str, SourceRecord]:
        """Load records keyed by source ID."""

    def save_records(self, records: Mapping[str, SourceRecord]) -> None:
        """Persist records keyed by source ID."""


class InMemorySourceStorage:
    """Volatile storage useful for tests and orchestration dry-runs."""

    def __init__(self, records: Mapping[str, SourceRecord] | None = None) -> None:
        self._records = dict(records or {})

    def load_records(self) -> dict[str, SourceRecord]:
        return dict(self._records)

    def save_records(self, records: Mapping[str, SourceRecord]) -> None:
        self._records = dict(records)


class JsonSourceStorage:
    """JSON-file storage with atomic replacement writes."""

    VERSION = 1

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def load_records(self) -> dict[str, SourceRecord]:
        if not self.path.exists():
            return {}

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SourceStorageError(f"failed to read source registry: {self.path}") from exc
        except json.JSONDecodeError as exc:
            raise SourceStorageError(f"source registry is not valid JSON: {self.path}") from exc

        if not isinstance(payload, dict):
            raise SourceStorageError("source registry payload must be a JSON object")
        if payload.get("version") != self.VERSION:
            raise SourceStorageError(
                f"unsupported source registry version: {payload.get('version')!r}"
            )

        raw_sources = payload.get("sources")
        if not isinstance(raw_sources, dict):
            raise SourceStorageError("source registry payload must include a sources object")

        records: dict[str, SourceRecord] = {}
        for raw_key, raw_record in raw_sources.items():
            try:
                source_id = normalize_source_id(raw_key)
                record = SourceRecord.from_dict(raw_record)
            except ValueError as exc:
                raise SourceStorageError(f"invalid source record for key {raw_key!r}") from exc

            if record.id != source_id:
                raise SourceStorageError(
                    f"source record id {record.id!r} does not match key {source_id!r}"
                )
            records[source_id] = record

        return records

    def save_records(self, records: Mapping[str, SourceRecord]) -> None:
        payload = {
            "version": self.VERSION,
            "sources": {
                source_id: records[source_id].to_dict()
                for source_id in sorted(records)
            },
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: str | None = None
        try:
            file_descriptor, temp_path = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                text=True,
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
            os.replace(temp_path, self.path)
        except OSError as exc:
            raise SourceStorageError(f"failed to write source registry: {self.path}") from exc
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)
