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

## Notes
- The pipeline uses category listings and can take time to finish.
- Use --limit-per-category for sampling or testing.
