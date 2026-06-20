"""Thin client for the randomuser.me API.

Sources only the *person* (name, username/gamertag, phone, portrait). Address
and DOB are generated locally (see :mod:`address` / :mod:`dob`) because
randomuser.me can't constrain state or age.
"""

from __future__ import annotations

import httpx

API_URL = "https://randomuser.me/api/"
_TIMEOUT = 15.0


class RandomUserError(RuntimeError):
    """Raised when randomuser.me is unreachable or returns an unexpected shape."""


def fetch_person(
    *,
    gender: str | None = None,
    nat: str = "us",
    client: httpx.Client | None = None,
) -> dict:
    """Fetch a single random person.

    Returns a dict with keys: ``first_name``, ``last_name``, ``gender``,
    ``username``, ``phone``, ``picture``, ``nat``.

    Args:
        gender: optional ``"male"`` / ``"female"`` filter.
        nat: nationality code (defaults to US so phone formatting matches).
        client: optional httpx client (injected for testing).
    """
    params: dict[str, str] = {"nat": nat, "inc": "name,login,gender,phone,cell,picture,nat"}
    if gender:
        params["gender"] = gender

    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT)
    try:
        resp = client.get(API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        raise RandomUserError(f"randomuser.me request failed: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    try:
        result = data["results"][0]
        name = result["name"]
        return {
            "first_name": name["first"],
            "last_name": name["last"],
            "gender": result.get("gender"),
            "username": result["login"]["username"],
            "phone": result.get("phone"),
            "picture": result.get("picture", {}).get("large"),
            "nat": result.get("nat"),
        }
    except (KeyError, IndexError, TypeError) as exc:
        raise RandomUserError("unexpected randomuser.me response") from exc
