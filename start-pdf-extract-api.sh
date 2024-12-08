#!/bin/bash

set -eo pipefail
cd deps/pdf-extract-api || exit

if [ ! -d ".venv" ]; then
  echo "Setting up virtual environment"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r app/requirements.txt
  cp .env.localhost.example .env.localhost
  chmod +x run.sh
else
  source .venv/bin/activate
fi

echo "Starting PDF Extract API"
./run.sh
