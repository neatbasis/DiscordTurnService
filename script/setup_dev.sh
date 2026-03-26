#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -e .[dev]
python -m pytest --version
PYTHONPATH=src python -m pytest -q
