"""Validate a US ZIP and resolve its real city via the Zippopotam.us API.

Zippopotam.us is a free, no-key service: ``GET /us/<zip>`` returns the real
city/state for an assigned ZIP, or ``404`` if the ZIP isn't real. We use it to
turn Faker's prefix-valid (but often fictional) ZIPs into ones PSN will accept,
and to pull the *actual* city for that ZIP so city/state/ZIP stay coherent.
"""

from __future__ import annotations

import httpx

API_BASE = "https://api.zippopotam.us/us"
_TIMEOUT = 10.0


class ZippopotamError(RuntimeError):
    """Raised when Zippopotam.us is unreachable or returns an unexpected shape."""


def lookup_zip(zip_code: str, *, client: httpx.Client | None = None) -> dict | None:
    """Resolve a US ZIP to its real place, or ``None`` if the ZIP isn't assigned.

    Returns a dict with keys ``city``, ``state``, ``state_abbr``, ``zip`` on a hit.
    A clean ``404`` (ZIP not real) returns ``None`` — only transport/shape errors
    raise.

    Args:
        zip_code: 5-digit US ZIP to validate.
        client: optional httpx client (injected for testing / connection reuse).

    Raises:
        ZippopotamError: on a network failure or an unexpected response shape.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    try:
        resp = client.get(f"{API_BASE}/{zip_code}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise ZippopotamError(f"zippopotam.us request failed: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    try:
        place = data["places"][0]
        return {
            "city": place["place name"],
            "state": place["state"],
            "state_abbr": place["state abbreviation"],
            "zip": data["post code"],
        }
    except (KeyError, IndexError, TypeError) as exc:
        raise ZippopotamError("unexpected zippopotam.us response") from exc
