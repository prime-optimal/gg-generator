"""Turn a randomuser.me username into a safe gamertag."""

from __future__ import annotations

import re

_INVALID = re.compile(r"[^A-Za-z0-9_]")


def to_gamertag(username: str) -> str:
    """Normalize a username into a gamertag of ``[A-Za-z0-9_]``.

    GuerrillaMail's local-part also accepts these characters, so the same value
    can seed the disposable email address.
    """
    tag = _INVALID.sub("", username)
    return tag or "player"
