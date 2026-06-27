default:
    @just --list

# Install deps + the project into the venv
sync:
    uv sync

# Run the CLI (e.g. `just run new --nat US`)
run *args:
    uv run gg {{args}}

# Generate a new profile
new *args:
    uv run gg new {{args}} --mail forward --state CA --op

# Export all profiles to CSV (e.g. `just export -o out.csv`)
export *args:
    uv run gg export {{args}}

# Build a standalone `gg` binary into ./dist (no Python needed to run it)
build:
    uv run pyinstaller --onefile --name gg --clean --noconfirm \
        --collect-all faker \
        src/gg_generator/__main__.py

# Build + install the binary to ~/.local/bin
install: build
    install -d ~/.local/bin
    install -m 0755 dist/gg ~/.local/bin/gg
    @echo "installed → ~/.local/bin/gg"

# Preview the release for the current pyproject.toml version (changes nothing)
release-dry:
    uv run python scripts/release.py --dry-run

# Cut a release for the current pyproject.toml version (bump it there first)
release:
    uv run python scripts/release.py

# Lint
lint:
    uv run ruff check .

# Format
fmt:
    uv run ruff format .

# Run tests
test:
    uv run pytest

# Lint + format-check + tests
check: lint
    uv run ruff format --check .
    uv run pytest
