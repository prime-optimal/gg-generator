"""Pluggable email backends.

- ``guerrilla``: GuerrillaMail disposable inbox (provisionable + pollable).
- ``forward``: a catch-all domain that forwards to a real inbox — we mint the
  address but there's no API to poll; mail lands in the controlled inbox.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from gg_generator.core.models import Mailbox
from gg_generator.mail.guerrillamail import GuerrillaMailClient, GuerrillaMailError

DEFAULT_FORWARD_DOMAIN = "braindeadfgc.lol"


class MailProviderError(RuntimeError):
    """Raised on provisioning failure or an unsupported operation for a backend."""


class MailProvider(ABC):
    name: str
    supports_inbox: bool = True

    @abstractmethod
    def provision(self, local_part: str) -> Mailbox:
        """Create (and return) an address whose local-part is ``local_part``."""

    def check_inbox(self, mailbox: Mailbox) -> list[dict]:
        raise MailProviderError(f"the '{self.name}' backend has no inbox to poll")

    def fetch(self, mailbox: Mailbox, mail_id: str) -> dict:
        raise MailProviderError(f"the '{self.name}' backend has no inbox to poll")


class GuerrillaProvider(MailProvider):
    name = "guerrilla"
    supports_inbox = True

    def provision(self, local_part: str) -> Mailbox:
        try:
            with GuerrillaMailClient() as gm:
                gm.get_address()  # mint a session/sid_token
                mailbox = gm.set_user(local_part)  # bind local-part
        except GuerrillaMailError as exc:
            raise MailProviderError(str(exc)) from exc
        mailbox.provider = self.name
        return mailbox

    def check_inbox(self, mailbox: Mailbox) -> list[dict]:
        try:
            with GuerrillaMailClient(sid_token=mailbox.sid_token) as gm:
                return gm.check_inbox()
        except GuerrillaMailError as exc:
            raise MailProviderError(str(exc)) from exc

    def fetch(self, mailbox: Mailbox, mail_id: str) -> dict:
        try:
            with GuerrillaMailClient(sid_token=mailbox.sid_token) as gm:
                return gm.fetch_email(mail_id)
        except GuerrillaMailError as exc:
            raise MailProviderError(str(exc)) from exc


class ForwardProvider(MailProvider):
    name = "forward"
    supports_inbox = False

    def __init__(self, domain: str = DEFAULT_FORWARD_DOMAIN) -> None:
        self.domain = domain

    def provision(self, local_part: str) -> Mailbox:
        return Mailbox(email=f"{local_part}@{self.domain}", provider=self.name)

    def check_inbox(self, mailbox: Mailbox) -> list[dict]:
        raise MailProviderError(
            f"'{self.domain}' forwards to your real inbox — check there, not here."
        )

    def fetch(self, mailbox: Mailbox, mail_id: str) -> dict:
        raise MailProviderError(
            f"'{self.domain}' forwards to your real inbox — check there, not here."
        )


def get_provider(backend: str, domain: str = DEFAULT_FORWARD_DOMAIN) -> MailProvider:
    """Build a provider by backend name (used when generating a new profile)."""
    if backend == "guerrilla":
        return GuerrillaProvider()
    if backend == "forward":
        return ForwardProvider(domain)
    raise MailProviderError(f"unknown mail backend: {backend!r}")


def provider_for(mailbox: Mailbox) -> MailProvider:
    """Reconstruct the provider that minted an existing mailbox."""
    if mailbox.provider == "forward":
        domain = mailbox.email.split("@", 1)[-1]
        return ForwardProvider(domain)
    return get_provider(mailbox.provider)
