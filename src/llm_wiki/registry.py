"""Source registry service."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import SOURCE_KINDS, SourceRecord, normalize_source_id, normalize_tags
from .storage import JsonSourceStorage, SourceStorage


class RegistryError(RuntimeError):
    """Base class for source registry errors."""


class InvalidSourceError(RegistryError):
    """Raised when a source definition is invalid."""


class DuplicateSourceError(RegistryError):
    """Raised when a source ID already exists."""


class SourceNotFoundError(RegistryError):
    """Raised when a source cannot be found."""


class SourceRegistry:
    """Register, validate, query, update, and remove source definitions."""

    def __init__(self, storage: SourceStorage | None = None) -> None:
        self._storage = storage
        self._records = storage.load_records() if storage is not None else {}

    @classmethod
    def from_json_file(cls, path: str | Path) -> SourceRegistry:
        """Create a registry backed by a JSON file."""

        return cls(JsonSourceStorage(path))

    def register_source(
        self,
        *,
        name: str,
        kind: str,
        location: str,
        source_id: str | None = None,
        description: str | None = None,
        tags: Iterable[str] | None = None,
        enabled: bool = True,
    ) -> SourceRecord:
        """Register a new source and persist it when storage is configured."""

        try:
            record_id = normalize_source_id(source_id or name)
        except ValueError as exc:
            raise InvalidSourceError(str(exc)) from exc

        if record_id in self._records:
            raise DuplicateSourceError(f"source already exists: {record_id}")

        try:
            record = SourceRecord(
                id=record_id,
                name=name,
                kind=kind,
                location=location,
                description=description,
                tags=tuple(tags or ()),
                enabled=enabled,
            )
        except ValueError as exc:
            raise InvalidSourceError(str(exc)) from exc

        self._records[record.id] = record
        self._persist()
        return record

    def get_source(self, source_id: str) -> SourceRecord:
        """Return a source by ID."""

        record_id = self._normalize_lookup_id(source_id)
        try:
            return self._records[record_id]
        except KeyError as exc:
            raise SourceNotFoundError(f"source not found: {record_id}") from exc

    def list_sources(
        self,
        *,
        kind: str | None = None,
        enabled: bool | None = None,
        tag: str | None = None,
    ) -> list[SourceRecord]:
        """List sources, optionally filtered by kind, enabled state, or tag."""

        records = list(self._records.values())

        if kind is not None:
            normalized_kind = kind.strip().lower()
            if normalized_kind not in SOURCE_KINDS:
                allowed = ", ".join(sorted(SOURCE_KINDS))
                raise InvalidSourceError(f"kind must be one of: {allowed}")
            records = [record for record in records if record.kind == normalized_kind]

        if enabled is not None:
            if not isinstance(enabled, bool):
                raise InvalidSourceError("enabled filter must be a boolean")
            records = [record for record in records if record.enabled is enabled]

        if tag is not None:
            normalized_tags = normalize_tags((tag,))
            if not normalized_tags:
                return []
            records = [record for record in records if normalized_tags[0] in record.tags]

        return sorted(records, key=lambda record: record.id)

    def update_source(self, source_id: str, **changes: object) -> SourceRecord:
        """Update mutable source fields and persist the result."""

        record = self.get_source(source_id)
        try:
            updated = record.with_updates(**changes)
        except ValueError as exc:
            raise InvalidSourceError(str(exc)) from exc

        if updated is record:
            return record

        self._records[record.id] = updated
        self._persist()
        return updated

    def remove_source(self, source_id: str) -> SourceRecord:
        """Remove a source by ID and return the deleted record."""

        record_id = self._normalize_lookup_id(source_id)
        try:
            removed = self._records.pop(record_id)
        except KeyError as exc:
            raise SourceNotFoundError(f"source not found: {record_id}") from exc

        self._persist()
        return removed

    def has_source(self, source_id: str) -> bool:
        """Return whether a source exists."""

        try:
            record_id = self._normalize_lookup_id(source_id)
        except InvalidSourceError:
            return False
        return record_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def _normalize_lookup_id(self, source_id: str) -> str:
        try:
            return normalize_source_id(source_id)
        except ValueError as exc:
            raise InvalidSourceError(str(exc)) from exc

    def _persist(self) -> None:
        if self._storage is not None:
            self._storage.save_records(self._records)
