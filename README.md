# gg-generator

A small CLI that mints a throwaway **gamertag + identity** and binds it to a
working email address — a [GuerrillaMail](https://www.guerrillamail.com/) disposable
inbox or your own forwarding catch-all domain — so you can spin up a gaming/account
persona, receive its verification mail, and optionally file it in 1Password.

- **Person** from [randomuser.me](https://randomuser.me/) (name, gamertag, phone, portrait).
- **US address** generated locally with Faker, then **validated against
  [Zippopotam.us](https://www.zippopotam.us/)**: pin a state and get a **real, assigned ZIP**
  with the **real city** for that ZIP plus a full street address — so city/state/ZIP stay
  coherent and PSN-acceptable (randomuser can't filter by state and its ZIP doesn't match).
- **DOB** constrained to a birth-year range (default floor **1980**, default ceiling = 18+).
- **Email backend** is pluggable:
  - `guerrilla` (default) — GuerrillaMail disposable inbox, pollable via `gg inbox`/`gg read`.
  - `forward` — a catch-all domain (`braindeadfgc.lol`) that forwards to a real inbox you
    control. No API to poll; mail lands in your real inbox.
- **Gamertag** derived from the username and reused as the email local-part.
- **Passwords** are 8+ chars with at least one digit and one uppercase letter.
- **1Password**: optionally push each profile as a Login item into the Developer vault
  (`op` CLI), inline with `gg new --op` or after the fact with `gg push`.
- **CSV export**: dump every profile to a single spreadsheet with `gg export`.
- **Standalone binary**: build a self-contained `gg` (no Python/uv needed) with `just build`.

## Setup

Tooling is pinned via [`mise`](https://mise.jdx.dev/) (`python 3.14`, `uv`, `hk`):

```bash
mise install      # provision toolchain
just sync         # uv sync — install deps + project
```

## Usage

```bash
just new                              # generate a profile (or: uv run gg new)
uv run gg new --state TX              # pin the US state (abbr or full name)
uv run gg new -s California --gender female
uv run gg new --min-year 1980 --max-year 1990   # constrain birth-year range
uv run gg new --mail forward                    # use the braindeadfgc.lol catch-all
uv run gg new --mail forward --domain other.tld # override the catch-all domain
uv run gg new --op                              # also save to 1Password (Developer vault)

uv run gg list                 # list generated profiles
uv run gg inbox <gamertag>     # check the bound inbox (guerrilla backend only)
uv run gg read <gamertag> <id> # read a message by id
uv run gg push <gamertag>            # push a saved profile to 1Password
uv run gg push <gamertag> --dry-run  # print the exact `op` command, run nothing

uv run gg export                     # export all profiles → profiles.csv
uv run gg export -o accounts.csv     # write to a specific file
uv run gg export -o -                # stream CSV to stdout
```

`gg export` writes one row per profile and a header row whose columns are the
**union of every field** across all profile JSONs, flattened to dot-notation
(`identity.first_name`, `identity.address.zip`, `mailbox.email`, …). Missing
fields (e.g. a profile with no address) render as empty cells. The CSV carries
the same throwaway-account data as `profiles/`, so it's git-ignored.

`gg new` options: `--state/-s`, `--min-year` (default 1980), `--max-year`
(default: most recent 18+ year), `--gender`, `--password-length`,
`--mail [guerrilla|forward]`, `--domain`, `--op`, `--vault`.

### 1Password

`--op` / `gg push` create a Login item via the `op` CLI. The item's **`username`
is the email** (sites autofill the email at sign-in), with the **gamertag in its
own field**, plus password, email, mail backend, full name, DOB, phone, and
address (city, state, ZIP). The item URL is the PSN sign-in host
(`my.account.sony.com`) so 1Password autofills both the PlayStation app and the
browser. Use `--dry-run` to preview the exact `op item create` command without
running it.

**Connecting `op`.** Install the [1Password CLI](https://developer.1password.com/docs/cli/)
and sign in so `op` has a session:

```bash
op signin                      # interactive, or use a service-account token
op vault list                  # find the vault name/uuid you want to write to
```

**Choosing the vault.** No vault is hardcoded. Resolution order is `--vault`
flag → `GG_OP_VAULT` env var → a vault literally named `Developer`. `op` accepts
either a vault name or its uuid:

```bash
gg push <gamertag> --vault "Game Accounts"   # explicit, per-invocation
export GG_OP_VAULT="Game Accounts"           # or set once for the shell/session
```

**With fnox.** Keep the vault id out of the repo by sourcing it through
[fnox](https://github.com/jdx/fnox). Copy `fnox.toml.example` to `fnox.toml`
(git-ignored) and set `GG_OP_VAULT` — either a literal vault name/uuid kept
local, or an `op://` reference so not even the id lives in the file:

```toml
# fnox.toml  (git-ignored)
[secrets]
GG_OP_VAULT = "op://Developer/gg-generator/vault_id"
```

```bash
fnox exec -- gg push <gamertag>   # GG_OP_VAULT injected from fnox / 1Password
```

Profiles persist to `./profiles/<gamertag>.json` (git-ignored). Each stores the
GuerrillaMail `sid_token`, so `inbox`/`read` keep working in later runs.

### Standalone binary

Package the CLI as a single self-contained executable (PyInstaller) that runs as
a bare `gg` with no Python or uv installed:

```bash
just build      # → ./dist/gg
just install    # build + copy to ~/.local/bin/gg
gg export -o accounts.csv
```

The binary is built for the host platform/arch (e.g. an Apple-silicon Mac
produces an arm64 binary) — rebuild on each target OS/arch you need to ship to.

## Layout

```
src/gg_generator/
├── cli.py                  # Typer app + subcommands
├── __main__.py             # entry point for `python -m gg_generator` / the binary
├── identity/
│   ├── builder.py          # composes person + address + DOB → Identity
│   ├── randomuser.py       # randomuser.me person client
│   ├── address.py          # Faker US address, ZIP validated via Zippopotam.us
│   ├── zippopotam.py       # Zippopotam.us ZIP→real-city validation
│   └── dob.py              # birth-year-constrained DOB
├── mail/
│   ├── providers.py        # backend abstraction: guerrilla | forward
│   └── guerrillamail.py    # GuerrillaMail session client
├── vault/onepassword.py    # push profiles into 1Password via `op`
├── core/models.py          # Identity / Address / Mailbox / Profile (pydantic)
├── core/store.py           # JSON profile persistence
├── core/export.py          # flatten profiles → CSV
├── gamertag.py             # username → gamertag
└── passwords.py            # policy-compliant password generation
```

## Develop

```bash
just test     # pytest (HTTP mocked — no network)
just lint     # ruff check
just fmt      # ruff format
just check    # lint + format-check + tests
```

## Releasing

`pyproject.toml`'s `version` is the **single source of truth**. To cut a release:
**bump `version` in `pyproject.toml`** and merge to `main`. The
`changelog` workflow (`scripts/release.py`) then regenerates the `CHANGELOG.md`
section for the new commit range, commits `chore(release): vX.Y.Z`, tags it, and
publishes a GitHub release. If the version isn't bumped, the workflow no-ops, so
ordinary merges never cut a release.

```bash
just release-dry   # preview the section for the current version (changes nothing)
just release       # cut it locally (CI does this for you on merge to main)
```
