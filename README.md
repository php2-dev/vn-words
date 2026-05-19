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

## Notes
- The pipeline uses category listings and can take time to finish.
- Use --limit-per-category for sampling or testing.

## Scripts
Clear generated data files:
- bash scripts/clear_data.sh

Clear and crawl full data, then filter:
- bash scripts/rebuild_full.sh
