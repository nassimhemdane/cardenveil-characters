#!/bin/sh
set -eu
export PYTHONPATH="${PYTHONPATH:-}:src"
python web/metadata.py init
python web/metadata.py validate
python web/build.py
(cd web/atelier-app && npm ci && npm run build)
