#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m ruff check .
