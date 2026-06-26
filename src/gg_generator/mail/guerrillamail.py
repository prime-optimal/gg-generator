"""Client for the GuerrillaMail public AJAX API.

No API key is required. The API is session-based: the first call mints a
``sid_token`` that every subsequent call must carry to address the same inbox.

Docs: https://www.guerrillamail.com/GuerrillaMailAPI.html
"""

from __future__ import annotations

import httpx

from gg_generator.core.models import Mailbox

API_URL = "https://api.guerrillamail.com/ajax.php"
USER_AGENT = "gg-generator/0.1 (+https://github.com/prime-optimal/gg-generator)"
_TIMEOUT = 20.0


class GuerrillaMailError(RuntimeError):
    """Raised on transport failure or an unexpected GuerrillaMail response."""


class GuerrillaMailClient:
    """Stateful GuerrillaMail session.

    Tracks ``sid_token`` across calls. Pass a saved token to resume a prior
    inbox; otherwise call :meth:`get_address` first to mint one.
    """

    def __init__(
        self,
        sid_token: str | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.sid_token = sid_token
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": USER_AGENT})

    # -- public API ---------------------------------------------------------

    def get_address(self) -> Mailbox:
        """Mint (or return the session's current) disposable address."""
        return self._to_mailbox(self._call("get_email_address"))

    def set_user(self, email_user: str) -> Mailbox:
        """Set the local-part of the address (e.g. bind it to a gamertag)."""
        data = self._call("set_email_user", email_user=email_user, lang="en")
        return self._to_mailbox(data)

    def check_inbox(self, seq: int = 0) -> list[dict]:
        """Return messages newer than sequence ``seq`` (0 = everything)."""
        return self._call("check_email", seq=seq).get("list", [])

    def list_emails(self, offset: int = 0) -> list[dict]:
        """Return a page of the inbox starting at ``offset``."""
        return self._call("get_email_list", offset=offset).get("list", [])

    def fetch_email(self, email_id: str) -> dict:
        """Fetch a single message (including its body) by id."""
        return self._call("fetch_email", email_id=email_id)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GuerrillaMailClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- internals ----------------------------------------------------------

    def _call(self, func: str, **params: object) -> dict:
        params["f"] = func
        if self.sid_token:
            params.setdefault("sid_token", self.sid_token)
        try:
            resp = self._client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise GuerrillaMailError(f"GuerrillaMail '{func}' failed: {exc}") from exc
        # Refresh the session token whenever the server hands one back.
        if isinstance(data, dict) and data.get("sid_token"):
            self.sid_token = data["sid_token"]
        return data

    def _to_mailbox(self, data: dict) -> Mailbox:
        try:
            return Mailbox(
                email=data["email_addr"],
                sid_token=self.sid_token or data.get("sid_token", ""),
                alias=data.get("alias"),
                created_ts=data.get("email_timestamp"),
            )
        except KeyError as exc:
            raise GuerrillaMailError("unexpected GuerrillaMail response") from exc
