"""`gg` command-line interface."""

from __future__ import annotations

import shlex
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gg_generator.core.export import profiles_to_csv
from gg_generator.core.models import Profile
from gg_generator.core.store import DEFAULT_DIR, ProfileStore
from gg_generator.identity.builder import build_identity
from gg_generator.identity.randomuser import RandomUserError
from gg_generator.mail.providers import (
    DEFAULT_FORWARD_DOMAIN,
    MailProviderError,
    get_provider,
    provider_for,
)
from gg_generator.passwords import MIN_LENGTH, generate_password
from gg_generator.vault.onepassword import (
    DEVELOPER_VAULT,
    OnePasswordError,
    create_login,
    op_available,
)


class MailBackend(str, Enum):
    guerrilla = "guerrilla"
    forward = "forward"

app = typer.Typer(
    help="gg — generate a gamertag + identity bound to a disposable or forwarding email.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_ProfilesDir = typer.Option(DEFAULT_DIR, "--profiles-dir", help="Where profiles are stored.")


@app.command()
def new(
    gender: str | None = typer.Option(None, help="Filter: male | female."),
    state: str | None = typer.Option(
        None, "--state", "-s", help="US state name or abbr (e.g. CA, Texas). Random if omitted."
    ),
    min_year: int = typer.Option(1980, "--min-year", help="Earliest birth year."),
    max_year: int | None = typer.Option(
        None, "--max-year", help="Latest birth year (default: most recent 18+ year)."
    ),
    password_length: int = typer.Option(
        MIN_LENGTH, "--password-length", min=MIN_LENGTH, help="Password length."
    ),
    mail: MailBackend = typer.Option(
        MailBackend.guerrilla, "--mail", help="Email backend: guerrilla | forward."
    ),
    domain: str = typer.Option(
        DEFAULT_FORWARD_DOMAIN, "--domain", help="Catch-all domain for --mail forward."
    ),
    save_op: bool = typer.Option(
        False, "--op/--no-op", help="Also save the profile to 1Password."
    ),
    vault: str = typer.Option(DEVELOPER_VAULT, "--vault", help="1Password vault for --op."),
    profiles_dir: Path = _ProfilesDir,
) -> None:
    """Generate an identity + gamertag bound to an email address."""
    store = ProfileStore(profiles_dir)

    with console.status("Building identity…"):
        try:
            identity = build_identity(
                gender=gender, state=state, min_year=min_year, max_year=max_year
            )
        except RandomUserError as exc:
            console.print(f"[red]Identity fetch failed:[/] {exc}")
            raise typer.Exit(1)
        except ValueError as exc:
            console.print(f"[red]Invalid option:[/] {exc}")
            raise typer.Exit(2)

    gamertag = identity.gamertag
    password = generate_password(password_length)

    provider = get_provider(mail.value, domain)
    with console.status(f"Provisioning {provider.name} address…"):
        try:
            mailbox = provider.provision(gamertag.lower())
        except MailProviderError as exc:
            console.print(f"[red]Address provisioning failed:[/] {exc}")
            raise typer.Exit(1)

    profile = Profile(
        gamertag=gamertag,
        password=password,
        identity=identity,
        mailbox=mailbox,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    path = store.save(profile)
    _print_profile(profile)
    console.print(f"[dim]saved → {path}[/]")
    if save_op:
        _save_to_op(profile, vault)


@app.command("list")
def list_profiles(profiles_dir: Path = _ProfilesDir) -> None:
    """List generated profiles."""
    profiles = ProfileStore(profiles_dir).list_profiles()
    if not profiles:
        console.print("[yellow]No profiles yet — run [bold]gg new[/].[/]")
        raise typer.Exit()

    table = Table(title="Profiles")
    for col in ("Gamertag", "Email", "Name", "Created"):
        table.add_column(col)
    for p in profiles:
        table.add_row(p.gamertag, p.mailbox.email, p.identity.full_name, p.created_at)
    console.print(table)


@app.command()
def export(
    output: Path = typer.Option(
        Path("profiles.csv"), "--output", "-o", help="CSV file to write (use '-' for stdout)."
    ),
    profiles_dir: Path = _ProfilesDir,
) -> None:
    """Export all profiles to a CSV — one row per profile, columns flattened from the JSON."""
    profiles = ProfileStore(profiles_dir).list_profiles()
    if not profiles:
        console.print("[yellow]No profiles to export — run [bold]gg new[/].[/]")
        raise typer.Exit()

    csv_text = profiles_to_csv(profiles)
    if str(output) == "-":
        # markup=False: CSV cells may contain '[...]' that Rich would treat as markup.
        console.print(csv_text, markup=False, end="")
        return

    output.write_text(csv_text)
    console.print(f"[green]Exported {len(profiles)} profile(s) →[/] {output}")


@app.command()
def inbox(
    key: str = typer.Argument(..., help="Gamertag or email address."),
    profiles_dir: Path = _ProfilesDir,
) -> None:
    """Check the inbox bound to a profile (GuerrillaMail backend only)."""
    profile = _load(profiles_dir, key)
    provider = provider_for(profile.mailbox)
    if not provider.supports_inbox:
        console.print(
            f"[yellow]{profile.mailbox.email}[/] uses the '{provider.name}' backend — "
            "it forwards to your real inbox, so there's nothing to poll here."
        )
        raise typer.Exit()

    with console.status(f"Checking inbox for {profile.mailbox.email}…"):
        try:
            messages = provider.check_inbox(profile.mailbox)
        except MailProviderError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(1)

    if not messages:
        console.print(f"[yellow]Inbox empty for {profile.mailbox.email}.[/]")
        return

    table = Table(title=f"Inbox — {profile.mailbox.email}")
    for col in ("ID", "From", "Subject", "Date"):
        table.add_column(col)
    for m in messages:
        table.add_row(
            str(m.get("mail_id", "")),
            m.get("mail_from", ""),
            m.get("mail_subject", ""),
            m.get("mail_date", ""),
        )
    console.print(table)


@app.command()
def read(
    key: str = typer.Argument(..., help="Gamertag or email address."),
    mail_id: str = typer.Argument(..., help="Message id from `gg inbox`."),
    profiles_dir: Path = _ProfilesDir,
) -> None:
    """Read a single message from a profile's inbox (GuerrillaMail backend only)."""
    profile = _load(profiles_dir, key)
    provider = provider_for(profile.mailbox)
    if not provider.supports_inbox:
        console.print(
            f"[yellow]{profile.mailbox.email}[/] forwards to your real inbox — read it there."
        )
        raise typer.Exit()

    with console.status(f"Fetching message {mail_id}…"):
        try:
            message = provider.fetch(profile.mailbox, mail_id)
        except MailProviderError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(1)

    header = (
        f"[bold]From:[/] {message.get('mail_from', '')}\n"
        f"[bold]Subject:[/] {message.get('mail_subject', '')}\n"
        f"[bold]Date:[/] {message.get('mail_date', '')}"
    )
    console.print(Panel(header, title=f"Message {mail_id}", expand=False))
    console.print(message.get("mail_body", "[dim](no body)[/]"))


@app.command()
def push(
    key: str = typer.Argument(..., help="Gamertag or email address."),
    vault: str = typer.Option(DEVELOPER_VAULT, "--vault", help="1Password vault id/name."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the `op` command instead of running it."
    ),
    profiles_dir: Path = _ProfilesDir,
) -> None:
    """Push a saved profile into 1Password as a Login item."""
    profile = _load(profiles_dir, key)

    if dry_run:
        result = create_login(profile, vault, dry_run=True)
        # markup=False: field assignments contain `[text]`, which Rich would treat as markup.
        console.print(" ".join(shlex.quote(arg) for arg in result["command"]), markup=False)
        return

    if not op_available():
        console.print("[red]`op` CLI not found on PATH (install the 1Password CLI).[/]")
        raise typer.Exit(1)
    _save_to_op(profile, vault)


# -- helpers ----------------------------------------------------------------


def _save_to_op(profile: Profile, vault: str) -> None:
    try:
        with console.status("Saving to 1Password…"):
            result = create_login(profile, vault)
    except OnePasswordError as exc:
        console.print(f"[yellow]1Password save skipped:[/] {exc}")
        return
    item_id = result.get("id", "?")
    console.print(f"[green]→ 1Password:[/] item [bold]{item_id}[/] in vault {vault}")


def _load(profiles_dir: Path, key: str) -> Profile:
    try:
        return ProfileStore(profiles_dir).load(key)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(1)


def _print_profile(profile: Profile) -> None:
    ident = profile.identity
    addr = ident.address
    lines = [
        f"[bold cyan]Gamertag[/]  {profile.gamertag}",
        f"[bold cyan]Email[/]     {profile.mailbox.email}",
        f"[bold cyan]Password[/]  {profile.password}",
        f"[bold cyan]Name[/]      {ident.full_name}",
        f"[bold cyan]Gender[/]    {ident.gender or '—'}",
        f"[bold cyan]DOB[/]       {ident.dob or '—'} (age {ident.age or '—'})",
        f"[bold cyan]Phone[/]     {ident.phone or '—'}",
    ]
    if addr:
        lines += [
            f"[bold cyan]Address[/]   {addr.street}",
            f"[bold cyan]City/St[/]   {addr.city}, {addr.state} ({addr.state_abbr})",
            f"[bold cyan]ZIP[/]       {addr.zip}",
        ]
    else:
        lines.append("[bold cyan]Address[/]   —")
    console.print(Panel("\n".join(lines), title="New profile", expand=False))


if __name__ == "__main__":
    app()
