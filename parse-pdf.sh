#!/bin/bash

PYTHONPATH="./:$PYTHONPATH" uv run python3 src/service/pdf_parser.py "$@"
