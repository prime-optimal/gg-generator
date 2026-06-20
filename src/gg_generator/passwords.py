"""Cryptographically-random password generation.

Policy (per project requirement): at least 8 characters, with at least one
digit and at least one uppercase letter.
"""

from __future__ import annotations

import secrets
import string

MIN_LENGTH = 8
_ALPHABET = string.ascii_letters + string.digits


def generate_password(length: int = MIN_LENGTH) -> str:
    """Return a random password guaranteed to contain >=1 digit and >=1 uppercase.

    Raises:
        ValueError: if ``length`` is below the minimum needed to satisfy the policy.
    """
    if length < MIN_LENGTH:
        raise ValueError(f"password length must be >= {MIN_LENGTH}")

    # Seed the guaranteed character classes, fill the rest from the full alphabet.
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        *(secrets.choice(_ALPHABET) for _ in range(length - 2)),
    ]

    # Fisher–Yates shuffle with a CSPRNG so the seeded chars aren't positionally fixed.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)
