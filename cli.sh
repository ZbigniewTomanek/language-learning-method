#!/bin/bash

PYTHONPATH="./:$PYTHONPATH" uv run src/app.py "$@"
