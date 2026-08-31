#!/bin/sh
set -eu
python -m pip install -e ".[pdf-assets]"
export PYTHONPATH="${PYTHONPATH:-}:src"
python web/metadata.py init
python web/metadata.py validate
python web/build.py
