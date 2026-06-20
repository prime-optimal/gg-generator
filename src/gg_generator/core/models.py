"""Domain models for generated profiles."""

from __future__ import annotations

from pydantic import BaseModel


class Address(BaseModel):
    """A US street address. State and ZIP are kept aligned; city is plausible."""

    street: str
    city: str
    state: str  # full name, e.g. "California"
    state_abbr: str  # e.g. "CA"
    zip: str
    country: str = "United States"

    @property
    def one_line(self) -> str:
        return f"{self.street}, {self.city}, {self.state_abbr} {self.zip}"


class Identity(BaseModel):
    """A fake person: identity fields from randomuser.me, address/DOB generated locally."""

    gamertag: str  # derived from login.username
    first_name: str
    last_name: str
    gender: str | None = None
    phone: str | None = None
    dob: str | None = None  # ISO date, e.g. "1985-03-12"
    age: int | None = None
    nat: str | None = None
    address: Address | None = None
    picture: str | None = None  # large portrait URL

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Mailbox(BaseModel):
    """An email address bound to a profile.

    ``provider`` records the backend: ``"guerrilla"`` (pollable disposable inbox)
    or ``"forward"`` (a catch-all domain that forwards to a real inbox — no API).
    ``sid_token`` is GuerrillaMail's session handle, needed to re-check that inbox;
    it's empty for the forward backend.
    """

    email: str
    provider: str = "guerrilla"
    sid_token: str = ""
    alias: str | None = None
    created_ts: int | None = None


class Profile(BaseModel):
    """A complete throwaway account: gamertag + credentials + identity + inbox."""

    gamertag: str
    password: str
    identity: Identity
    mailbox: Mailbox
    created_at: str  # ISO timestamp
