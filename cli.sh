#!/bin/bash

PYTHONPATH="./:$PYTHONPATH" uv run src/app/main.py "$@"
