# Wiktionary Vietnamese POS pipeline

This project collects Vietnamese nouns, verbs, and adjectives from vi.wiktionary.org using the MediaWiki API and saves them to JSONL or CSV.

## Quick start
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. python src/main.py --output data/vi_wiktionary_pos.jsonl

## Output schema
- title
- pos (noun | verb | adjective)
- definitions (list of cleaned definitions)
- source_url

## Filtering (rule-based + frequency)
You can filter on a sample file; no need to run the full crawl to test rules.

Basic filtering:
1. python src/filter_words.py --input data/sample.jsonl --output data/sample.filtered.jsonl
2. python src/filter_words.py --input data/sample.jsonl --output data/sample.filtered.jsonl --reject-output data/sample.rejected.jsonl --report data/filter_report.json

Filtering with frequency data:
1. python src/filter_words.py --input data/vi_wiktionary_pos.jsonl --freq-file data/vi_freq.tsv --min-freq 5 --output data/vi.filtered.jsonl

Frequency file formats:
- word<TAB>freq (tsv)
- word,freq (csv)
- word (one per line)

## Scoring and ranking
Score words using explainable components: clean, pleasant, readable, native_vi,
and frequency.

1. python src/score_words.py --input data/vi_wiktionary_pos.jsonl --output data/vi_wiktionary_scored.jsonl --report data/vi_wiktionary_scoring_report.json
2. python src/ai_label_words.py --provider ollama --model qwen2.5:7b-instruct --input data/vi_wiktionary_scored.jsonl --output data/word_ai_labels.csv --limit 1000 --batch-size 8
3. python src/apply_word_labels.py --input data/vi_wiktionary_scored.jsonl --labels data/word_ai_labels.csv --output data/vi_wiktionary_calibrated.jsonl
4. python src/select_words.py --input data/vi_wiktionary_calibrated.jsonl --output data/vi_wiktionary_selected.csv --format csv --min-score 0.78 --limit 500

See docs/word_scoring_method.md for the scoring method and calibration plan.

## Notes
- The pipeline uses category listings and can take time to finish.
- Use --limit-per-category for sampling or testing.

## Scripts
Clear generated data files:
- bash scripts/clear_data.sh

Clear and crawl full data, then filter:
- bash scripts/rebuild_full.sh
