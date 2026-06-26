"""Flatten saved profiles into a single CSV (one row per profile)."""

from __future__ import annotations

import csv
import io
from typing import Any

from gg_generator.core.models import Profile


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict into dot-notation keys.

    ``{"identity": {"address": {"zip": "1"}}}`` -> ``{"identity.address.zip": "1"}``.
    Non-dict values (including ``None`` and lists) are kept as-is.
    """
    flat: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, prefix=f"{full_key}."))
        else:
            flat[full_key] = value
    return flat


def collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    """Union of all keys across rows, preserving first-seen order."""
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return fieldnames


def profiles_to_csv(profiles: list[Profile]) -> str:
    """Render profiles as CSV text: a header row plus one row per profile."""
    rows = [flatten(p.model_dump()) for p in profiles]
    fieldnames = collect_fieldnames(rows)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return buffer.getvalue()
