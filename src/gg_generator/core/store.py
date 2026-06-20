"""On-disk persistence for generated profiles (one JSON file per gamertag)."""

from __future__ import annotations

from pathlib import Path

from gg_generator.core.models import Profile

DEFAULT_DIR = Path("profiles")


class ProfileStore:
    """A flat directory of ``<gamertag>.json`` profile files."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_DIR

    def save(self, profile: Profile) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(profile.gamertag)
        path.write_text(profile.model_dump_json(indent=2))
        return path

    def load(self, key: str) -> Profile:
        """Load a profile by gamertag (fast path) or by email (scan)."""
        path = self._path(key)
        if path.exists():
            return Profile.model_validate_json(path.read_text())
        for profile in self.list_profiles():
            if key.lower() in (profile.gamertag.lower(), profile.mailbox.email.lower()):
                return profile
        raise FileNotFoundError(f"no profile found for '{key}'")

    def list_profiles(self) -> list[Profile]:
        return [Profile.model_validate_json(p.read_text()) for p in self._paths()]

    # -- internals ----------------------------------------------------------

    def _paths(self) -> list[Path]:
        if not self.base_dir.exists():
            return []
        return sorted(self.base_dir.glob("*.json"))

    def _path(self, gamertag: str) -> Path:
        return self.base_dir / f"{gamertag.lower()}.json"
