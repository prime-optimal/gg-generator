#!/usr/bin/env python3
"""Release driver — pyproject.toml is the single source of truth for the version.

Workflow: bump ``version`` in ``pyproject.toml``, merge to ``main``. This script
(run by .github/workflows/changelog.yml, or locally via ``just release``) then:

  1. reads the version from pyproject.toml,
  2. no-ops if a tag for that version already exists (so ordinary, non-bumping
     commits never cut a release — idempotent),
  3. regenerates the CHANGELOG section for the new commit range with changelogen,
  4. prepends it to CHANGELOG.md, commits ``chore(release): vX.Y.Z``, tags it,
     pushes, and (best-effort) creates a matching GitHub release.

changelogen only formats the commit groups; the version/tag come from pyproject.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"


def run(*args: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=ROOT, text=True, capture_output=capture, check=check)


def git(*args: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", *args, capture=capture, check=check)


def read_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def tag_exists(tag: str) -> bool:
    return (
        git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", capture=True, check=False).returncode
        == 0
    )


def last_tag() -> str | None:
    res = git("describe", "--tags", "--abbrev=0", capture=True, check=False)
    return (res.stdout.strip() or None) if res.returncode == 0 else None


def generate_section(tag: str, since: str | None) -> str:
    """Build the CHANGELOG section for ``since..HEAD`` under a ``## <tag>`` header."""
    cmd = ["bunx", "changelogen@latest"]
    if since:
        cmd += ["--from", since]
    md = run(*cmd, capture=True).stdout

    out: list[str] = []
    header_done = False
    for line in md.splitlines():
        if not header_done and line.startswith("## "):
            out.append(f"## {tag}")  # changelogen's range header → the real version
            header_done = True
            continue
        line = re.sub(r"\.\.\.main\)", f"...{tag})", line)  # compare link → the real tag range
        out.append(line)
    return "\n".join(out).strip("\n")


def prepend_changelog(section: str) -> None:
    existing = CHANGELOG.read_text() if CHANGELOG.exists() else "# Changelog\n"
    lines = existing.splitlines()
    if lines and lines[0].startswith("# "):
        title, rest = lines[0], "\n".join(lines[1:]).strip("\n")
    else:
        title, rest = "# Changelog", existing.strip("\n")
    new = f"{title}\n\n{section}\n"
    if rest:
        new += f"\n{rest}\n"
    CHANGELOG.write_text(new)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print the section, change nothing.")
    ap.add_argument("--no-push", action="store_true", help="commit + tag locally, don't push.")
    args = ap.parse_args()

    version = read_version()
    tag = f"v{version}"
    if tag_exists(tag):
        print(
            f"tag {tag} already exists — version not bumped in pyproject.toml, nothing to release."
        )
        return 0

    since = last_tag()
    section = generate_section(tag, since)
    print(section)
    if args.dry_run:
        print(f"\n[dry-run] would release {tag} (since {since or 'repo start'})")
        return 0

    prepend_changelog(section)
    git("add", "CHANGELOG.md")
    git("commit", "-m", f"chore(release): {tag}")
    git("tag", "-a", tag, "-m", tag)
    if not args.no_push:
        git("push", "origin", "HEAD")
        git("push", "origin", tag)
        run("gh", "release", "create", tag, "--title", tag, "--notes", section, check=False)
    print(f"\nreleased {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
