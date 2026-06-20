"""US address generation with a selectable state and a state-aligned ZIP.

randomuser.me can't filter by state and its ZIP doesn't match the state, so we
generate the address locally with Faker. ``zipcode_in_state`` yields a ZIP whose
prefix matches the chosen state; the city is plausible but not guaranteed to be
the real city for that ZIP.
"""

from __future__ import annotations

from faker import Faker

from gg_generator.core.models import Address

_fake = Faker("en_US")

# 50 states + DC. Abbreviation -> full name.
US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
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


def generate_address(state: str | None = None) -> Address:
    """Generate a US address, optionally pinned to ``state`` (name or abbr)."""
    abbr = normalize_state(state) if state else _fake.state_abbr(include_territories=False)
    return Address(
        street=_fake.street_address(),
        city=_fake.city(),
        state=US_STATES[abbr],
        state_abbr=abbr,
        zip=_fake.zipcode_in_state(state_abbr=abbr),
    )
