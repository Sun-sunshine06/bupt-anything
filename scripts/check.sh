#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --frozen ruff check .
uv run --frozen pytest -q
uv run --frozen bupt-agent doctor
