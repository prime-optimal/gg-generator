"""US address generation with a selectable state and a real, validated ZIP.

randomuser.me can't filter by state and its ZIP doesn't match the state, so the
address is built locally. Faker proposes a state-prefixed ZIP candidate; that
candidate is validated against Zippopotam.us, and the *real* city for the
resolved ZIP is used — so city/state/ZIP stay coherent and PSN-acceptable. We
retry with fresh candidates until a real ZIP is found (Faker's range-based ZIPs
are frequently unassigned).
"""

from __future__ import annotations

import httpx
from faker import Faker

from gg_generator.core.models import Address
from gg_generator.identity.zippopotam import lookup_zip

_fake = Faker("en_US")

# How many Faker ZIP candidates to validate before giving up on a state.
_MAX_ZIP_ATTEMPTS = 15


class AddressError(RuntimeError):
    """Raised when no real ZIP could be resolved for the chosen state."""


# 50 states + DC. Abbreviation -> full name.
US_STATES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
_NAME_TO_ABBR = {name.lower(): abbr for abbr, name in US_STATES.items()}


def normalize_state(state: str) -> str:
    """Resolve a state name or abbreviation to its 2-letter code.

    Raises:
        ValueError: if ``state`` isn't a recognized US state/DC.
    """
    key = state.strip()
    if key.upper() in US_STATES:
        return key.upper()
    if key.lower() in _NAME_TO_ABBR:
        return _NAME_TO_ABBR[key.lower()]
    raise ValueError(f"unknown US state: {state!r}")


def generate_address(
    state: str | None = None,
    *,
    client: httpx.Client | None = None,
    attempts: int = _MAX_ZIP_ATTEMPTS,
) -> Address:
    """Generate a US address with a real, validated ZIP.

    Pins to ``state`` (name or abbr) when given, otherwise random. The ZIP is
    validated against Zippopotam.us and the city is taken from the resolved real
    place, so the address is coherent and PSN-acceptable.

    Args:
        state: US state name or abbreviation (random if None).
        client: optional httpx client (injected for testing / connection reuse).
        attempts: max Faker ZIP candidates to validate before failing.

    Raises:
        ValueError: on an unknown state.
        ZippopotamError: on a network/transport failure.
        AddressError: if no real ZIP resolved within ``attempts`` tries.
    """
    abbr = normalize_state(state) if state else _fake.state_abbr(include_territories=False)

    for _ in range(attempts):
        candidate = _fake.zipcode_in_state(state_abbr=abbr)
        place = lookup_zip(candidate, client=client)
        # Keep only hits that actually fall in the requested state (a ZIP prefix
        # can occasionally straddle a border).
        if place and place["state_abbr"] == abbr:
            return Address(
                street=_fake.street_address(),
                city=place["city"],
                state=place["state"],
                state_abbr=place["state_abbr"],
                zip=place["zip"],
            )

    raise AddressError(
        f"no real ZIP found for {abbr} after {attempts} attempts (Zippopotam.us returned no match)"
    )
