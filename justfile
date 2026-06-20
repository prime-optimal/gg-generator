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
    uv run gg new {{args}}

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
