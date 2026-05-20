#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-qwen2.5:7b-instruct}"
LIMIT="${LIMIT:-500}"
BATCH_SIZE="${BATCH_SIZE:-8}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Install it from https://ollama.com/download"
  exit 1
fi

if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama is not running. Start it with: ollama serve"
  exit 1
fi

ollama pull "$MODEL"

python src/score_words.py \
  --input data/vi_wiktionary_pos.jsonl \
  --output data/vi_wiktionary_scored.jsonl \
  --report data/vi_wiktionary_scoring_report.json

python src/ai_label_words.py \
  --provider ollama \
  --model "$MODEL" \
  --input data/vi_wiktionary_scored.jsonl \
  --output data/word_ai_labels.csv \
  --cache data/word_ai_label_cache.local.jsonl \
  --limit "$LIMIT" \
  --batch-size "$BATCH_SIZE" \
  --min-score 0.70

python src/apply_word_labels.py \
  --input data/vi_wiktionary_scored.jsonl \
  --labels data/word_ai_labels.csv \
  --output data/vi_wiktionary_calibrated.jsonl

python src/select_words.py \
  --input data/vi_wiktionary_calibrated.jsonl \
  --output data/vi_wiktionary_selected.csv \
  --format csv \
  --min-score 0.78 \
  --limit 500
