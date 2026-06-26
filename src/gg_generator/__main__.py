"""Entry point for `python -m gg_generator` and the PyInstaller binary."""

from __future__ import annotations

from gg_generator.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
