"""Push generated profiles into 1Password via the `op` CLI.

Creates a Login item per profile in the Developer vault. The subprocess runner
is injectable so the argument-building and error handling are unit-testable
without touching a live vault.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable

from gg_generator.core.models import Profile

# Target vault for new Login items. `op` resolves either a vault name or id, so
# set GG_OP_VAULT to your vault's name/uuid (e.g. via fnox/your shell), or pass
# --vault per invocation. Defaults to a vault literally named "Developer".
DEFAULT_VAULT = os.environ.get("GG_OP_VAULT", "Developer")

# PlayStation/PSN sign-in. 1Password matches autofill on host, so the bare host
# covers both the PlayStation app and the browser sign-in page.
PSN_SIGNIN_URL = "https://my.account.sony.com"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class OnePasswordError(RuntimeError):
    """Raised when the `op` CLI is missing or returns a non-zero exit."""


def op_available() -> bool:
    return shutil.which("op") is not None


def build_create_args(profile: Profile, vault: str = DEFAULT_VAULT) -> list[str]:
    """Assemble the `op item create` argv for a profile (a Login item)."""
    ident = profile.identity
    addr = ident.address

    fields = [
        # 1Password autofills `username` at sign-in — sites use the email, so this
        # must be the email. The gamertag lives in its own field below.
        f"username={profile.mailbox.email}",
        f"password={profile.password}",
        f"gamertag[text]={profile.gamertag}",
        f"email[text]={profile.mailbox.email}",
        f"mail_backend[text]={profile.mailbox.provider}",
        f"full_name[text]={ident.full_name}",
        f"gender[text]={ident.gender or ''}",
        f"date_of_birth[text]={ident.dob or ''}",
        f"phone[text]={ident.phone or ''}",
    ]
    if addr:
        fields += [
            f"address[text]={addr.one_line}",
            f"city[text]={addr.city}",
            f"state[text]={addr.state_abbr}",
            f"zip[text]={addr.zip}",
        ]
    if profile.mailbox.sid_token:
        fields.append(f"guerrilla_sid_token[password]={profile.mailbox.sid_token}")

    return [
        "op", "item", "create",
        "--category=login",
        f"--vault={vault}",
        f"--title={profile.gamertag}",
        f"--url={PSN_SIGNIN_URL}",
        "--tags=gg-generator",
        "--format=json",
        *fields,
    ]


def create_login(
    profile: Profile,
    vault: str = DEFAULT_VAULT,
    *,
    runner: Runner = subprocess.run,
    dry_run: bool = False,
) -> dict:
    """Create a Login item for ``profile``.

    Returns the parsed `op` JSON on success, or ``{"dry_run": True, "command": [...]}``
    when ``dry_run`` is set.

    Raises:
        OnePasswordError: if `op` is missing or exits non-zero.
    """
    args = build_create_args(profile, vault)
    if dry_run:
        return {"dry_run": True, "command": args}
    # Only gate on a real binary for the default runner; injected runners (tests) bypass.
    if runner is subprocess.run and not op_available():
        raise OnePasswordError("`op` CLI not found on PATH (install the 1Password CLI).")

    proc = runner(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise OnePasswordError(proc.stderr.strip() or "op item create failed")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}
