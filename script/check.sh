#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m ruff check .
