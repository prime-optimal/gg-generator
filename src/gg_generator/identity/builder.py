"""Compose a full :class:`Identity` from a randomuser person + local address/DOB."""

from __future__ import annotations

import httpx

from gg_generator.core.models import Identity
from gg_generator.gamertag import to_gamertag
from gg_generator.identity import randomuser
from gg_generator.identity.address import generate_address
from gg_generator.identity.dob import DEFAULT_MIN_YEAR, generate_dob


def build_identity(
    *,
    gender: str | None = None,
    state: str | None = None,
    min_year: int = DEFAULT_MIN_YEAR,
    max_year: int | None = None,
    client: httpx.Client | None = None,
) -> Identity:
    """Fetch a person and attach a state-pinned US address + constrained DOB.

    Args:
        gender: ``"male"`` / ``"female"`` filter for the person.
        state: US state name or abbreviation to pin the address to (random if None).
        min_year: earliest birth year (default 1980).
        max_year: latest birth year (default: most recent 18+ year).

    Raises:
        RandomUserError: on person-fetch failure.
        ValueError: on an unknown state or an empty birth-year range.
    """
    person = randomuser.fetch_person(gender=gender, client=client)
    address = generate_address(state, client=client)
    dob, age = generate_dob(min_year, max_year)

    return Identity(
        gamertag=to_gamertag(person["username"]),
        first_name=person["first_name"],
        last_name=person["last_name"],
        gender=person["gender"],
        phone=person["phone"],
        dob=dob,
        age=age,
        nat=person["nat"],
        address=address,
        picture=person["picture"],
    )
