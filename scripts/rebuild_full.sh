#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${1:-data}"

./scripts/clear_data.sh "$DATA_DIR"

python src/main.py --output "$DATA_DIR/vi_wiktionary_pos.jsonl" --sleep 0.1

python src/filter_words.py \
  --input "$DATA_DIR/vi_wiktionary_pos.jsonl" \
  --output "$DATA_DIR/vi.filtered.jsonl" \
  --report "$DATA_DIR/filter_report.json"

echo "Rebuild complete"
