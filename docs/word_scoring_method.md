# Vietnamese word scoring method

This project scores Wiktionary Vietnamese words with an explainable hybrid model.
The first version is deterministic: it uses rules and small lexicons, then writes
component scores that can later be replaced or calibrated with LLM/human labels.

## Output

`src/score_words.py` reads JSONL items with:

- `title`
- `pos`
- `definitions`
- `source_url`

It writes each candidate with:

- `scores.clean`
- `scores.pleasant`
- `scores.readable`
- `scores.native_vi`
- `scores.frequency`
- `scores.overall`
- `flags`
- `features`
- `rejected`

## Score components

Default overall score:

```text
overall =
  0.20 * clean
+ 0.35 * pleasant
+ 0.20 * readable
+ 0.15 * native_vi
+ 0.10 * frequency
```

### `clean`

Filters profanity, digits, invalid word shape, missing vowel-like sounds, and
meta/technical Wiktionary definitions. This score is intentionally strict.
Rows with hard reject flags are marked `rejected`.

### `readable`

Rewards short Vietnamese-looking words, especially 2-3 syllables. It penalizes
hyphenation, uppercase forms, very long words, too many syllables, and syllables
that are difficult to pronounce.

### `native_vi`

Estimates whether the word feels native/common Vietnamese rather than heavily
Sino-Vietnamese or borrowed. This is a soft score. It uses a seed list of
Sino-Vietnamese syllables, loanword markers, hyphenated transliterations, and
definition markers such as "phiên âm" or "mượn".

### `pleasant`

This is the most subjective component. The deterministic version uses weak
positive/negative sound and meaning markers, plus small bonuses for compact
2-3 syllable forms. For production quality ranking, replace or calibrate this
component with human labels or LLM judgments.

### `frequency`

Without a frequency file, this component is neutral-low (`0.40`) and gets a
`missing_frequency_source` flag. With a frequency file, values are log-scaled.

## Human calibration

The preferred workflow is AI-first labeling, then human final review.

Local/free-ish labeling with Ollama:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct

python src/ai_label_words.py \
  --provider ollama \
  --model qwen2.5:7b-instruct \
  --input data/vi_wiktionary_scored.jsonl \
  --output data/word_ai_labels.csv \
  --limit 1000 \
  --batch-size 8
```

The model weights are free to run locally, but you pay with local compute time,
RAM, and electricity. Smaller models are cheaper/faster but less reliable for
Vietnamese nuance.

Suggested local models:

- `qwen2.5:7b-instruct`: good default for normal laptops with enough RAM.
- `qwen2.5:3b-instruct`: faster/lighter, lower nuance.
- `llama3.1:8b-instruct`: reasonable general model, Vietnamese quality varies.

Start with `--limit 100` before labeling thousands of words.

OpenAI API labeling:

```bash
OPENAI_API_KEY=... python src/ai_label_words.py \
  --input data/vi_wiktionary_scored.jsonl \
  --output data/word_ai_labels.csv \
  --limit 1000 \
  --batch-size 20
```

The script uses OpenAI's Responses API with Structured Outputs and a strict
JSON schema. It also writes `data/word_ai_label_cache.jsonl`, so interrupted
runs can resume without relabeling completed words.

Apply AI labels:

```bash
python src/apply_word_labels.py \
  --input data/vi_wiktionary_scored.jsonl \
  --labels data/word_ai_labels.csv \
  --output data/vi_wiktionary_calibrated.jsonl
```

Then review the final selected CSV manually.

You can also export a stratified manual sample:

```bash
python src/export_label_sample.py \
  --input data/vi_wiktionary_scored.jsonl \
  --output data/word_label_sample.csv \
  --size 600
```

Fill these columns:

- `label_keep`: `1` to keep, `0` to reject.
- `label_pleasant`: 0-5, subjective beauty/pleasantness.
- `label_readable`: 0-5, ease of reading/writing.
- `label_native_vi`: 0-5, natural Vietnamese feel.
- `label_note`: optional reason.

Apply labels:

```bash
python src/apply_word_labels.py \
  --input data/vi_wiktionary_scored.jsonl \
  --labels data/word_label_sample.csv \
  --output data/vi_wiktionary_calibrated.jsonl
```

Then select from the calibrated file:

```bash
python src/select_words.py \
  --input data/vi_wiktionary_calibrated.jsonl \
  --output data/vi_wiktionary_selected.csv \
  --format csv \
  --min-score 0.78 \
  --limit 500
```

## Recommended workflow

1. Crawl Wiktionary:

```bash
python src/main.py --output data/vi_wiktionary_pos.jsonl
```

2. Score words:

```bash
python src/score_words.py \
  --input data/vi_wiktionary_pos.jsonl \
  --output data/vi_wiktionary_scored.jsonl \
  --report data/vi_wiktionary_scoring_report.json
```

3. Select ranked candidates:

```bash
python src/select_words.py \
  --input data/vi_wiktionary_scored.jsonl \
  --output data/vi_wiktionary_selected.csv \
  --format csv \
  --min-score 0.70 \
  --limit 500
```

4. Review the selected file manually, then add missed profanity, bad loanwords,
or bad Sino-Vietnamese markers to optional lexicon files.

## Optional lexicons

All lexicon files are one phrase per line, with `#` comments allowed:

```bash
python src/score_words.py \
  --profanity-file data/lexicons/profanity.txt \
  --sino-file data/lexicons/sino_vietnamese_syllables.txt \
  --loanword-file data/lexicons/loanword_markers.txt
```

## Next calibration step

For a stronger model:

1. Select 1,000-3,000 representative words across score buckets.
2. Label `pleasant`, `natural`, `easy`, and `avoid` with a fixed rubric.
3. Train a small ranker from the deterministic features and labels.
4. Keep `clean` as a hard rule-based safety layer.
