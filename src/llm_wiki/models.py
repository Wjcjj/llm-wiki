"""Domain models for the source registry."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import re
from typing import Any, Iterable


SOURCE_KINDS = frozenset({"api", "database", "feed", "file", "manual", "web"})

_SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")
_SOURCE_ID_SANITIZER = re.compile(r"[^a-z0-9_-]+")
_SOURCE_ID_SEPARATOR = re.compile(r"[-_]{2,}")


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def normalize_source_id(value: str) -> str:
    """Normalize user-provided source IDs into stable registry keys."""

    if not isinstance(value, str):
        raise ValueError("source id must be a string")

    normalized = value.strip().lower()
    normalized = _SOURCE_ID_SANITIZER.sub("-", normalized)
    normalized = _SOURCE_ID_SEPARATOR.sub("-", normalized).strip("-_")

    if not normalized:
        raise ValueError("source id cannot be empty")
    if not _SOURCE_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "source id must contain only lowercase letters, digits, hyphens, "
            "or underscores, and must start and end with a letter or digit"
        )

    return normalized


def normalize_tags(tags: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize tags while preserving their first-seen order."""

    if tags is None:
        return ()

    normalized_tags: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError("tags must be strings")

        normalized = " ".join(tag.strip().lower().split())
        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        normalized_tags.append(normalized)

    return tuple(normalized_tags)


def _require_text(field_name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")

    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("description must be a string when provided")

    normalized = value.strip()
    return normalized or None


def _coerce_datetime(field_name: str, value: datetime | str) -> datetime:
    if isinstance(value, str):
        candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError(f"{field_name} must be a datetime")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """An immutable source definition tracked by the registry."""

    id: str
    name: str
    kind: str
    location: str
    description: str | None = None
    tags: tuple[str, ...] = ()
    enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        source_id = normalize_source_id(self.id)
        name = _require_text("name", self.name)
        kind = _require_text("kind", self.kind).lower()
        location = _require_text("location", self.location)
        description = _optional_text(self.description)
        tags = normalize_tags(self.tags)
        created_at = _coerce_datetime("created_at", self.created_at)
        updated_at = _coerce_datetime("updated_at", self.updated_at)

        if kind not in SOURCE_KINDS:
            allowed = ", ".join(sorted(SOURCE_KINDS))
            raise ValueError(f"kind must be one of: {allowed}")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if updated_at < created_at:
            raise ValueError("updated_at cannot be earlier than created_at")

        object.__setattr__(self, "id", source_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the source record into JSON-safe primitives."""

        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "location": self.location,
            "description": self.description,
            "tags": list(self.tags),
            "enabled": self.enabled,
            "created_at": _format_datetime(self.created_at),
            "updated_at": _format_datetime(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceRecord:
        """Build a source record from persisted data."""

        if not isinstance(data, dict):
            raise ValueError("source record must be a mapping")

        required_fields = {"id", "name", "kind", "location"}
        missing = sorted(required_fields.difference(data))
        if missing:
            raise ValueError(f"source record is missing required fields: {missing}")

        return cls(
            id=data["id"],
            name=data["name"],
            kind=data["kind"],
            location=data["location"],
            description=data.get("description"),
            tags=tuple(data.get("tags") or ()),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", utc_now()),
            updated_at=data.get("updated_at", data.get("created_at", utc_now())),
        )

    def with_updates(self, **changes: Any) -> SourceRecord:
        """Return a new record with mutable fields changed."""

        allowed_fields = {"description", "enabled", "kind", "location", "name", "tags"}
        unknown_fields = sorted(set(changes).difference(allowed_fields))
        if unknown_fields:
            raise ValueError(f"cannot update immutable or unknown fields: {unknown_fields}")
        if not changes:
            return self

        return replace(self, **changes, updated_at=utc_now())
