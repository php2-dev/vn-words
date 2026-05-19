#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${1:-data}"

if [[ ! -d "$DATA_DIR" ]]; then
  echo "Data directory not found: $DATA_DIR" >&2
  exit 1
fi

rm -f "$DATA_DIR"/*.jsonl "$DATA_DIR"/*.json "$DATA_DIR"/*.csv

echo "Cleared data files in $DATA_DIR"
