from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable

from wiktionary_vi.filtering import (
    DEFAULT_STOP_PHRASES,
    FilterConfig,
    evaluate_item,
    load_frequency_file,
    load_stop_phrases,
)


def _read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            yield json.loads(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter Wiktionary words using rules and frequency data."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_pos.jsonl",
        help="Input JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_pos.filtered.jsonl",
        help="Output JSONL file with kept items.",
    )
    parser.add_argument(
        "--reject-output",
        default=None,
        help="Optional JSONL file with rejected items and reasons.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report with counts by reason.",
    )
    parser.add_argument("--min-length", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=12)
    parser.add_argument(
        "--allow-uppercase",
        action="store_true",
        help="Allow words with uppercase letters.",
    )
    parser.add_argument(
        "--freq-file",
        default=None,
        help="Frequency file (word<TAB>freq, word,freq, or one word per line).",
    )
    parser.add_argument(
        "--min-freq",
        type=float,
        default=None,
        help="Minimum frequency threshold.",
    )
    parser.add_argument(
        "--require-freq",
        action="store_true",
        help="Reject words missing from the frequency file.",
    )
    parser.add_argument(
        "--stop-phrases-file",
        default=None,
        help="Additional stop phrases (one per line).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.min_freq is not None and args.freq_file is None:
        raise SystemExit("--min-freq requires --freq-file")

    freq_map = None
    if args.freq_file:
        freq_map = load_frequency_file(Path(args.freq_file))

    stop_phrases = DEFAULT_STOP_PHRASES
    if args.stop_phrases_file:
        stop_phrases = stop_phrases + load_stop_phrases(
            Path(args.stop_phrases_file)
        )

    config = FilterConfig(
        min_length=args.min_length,
        max_length=args.max_length,
        require_lowercase=not args.allow_uppercase,
        stop_phrases=stop_phrases,
        freq_min=args.min_freq,
        freq_map=freq_map,
        require_freq=args.require_freq,
    )

    reason_counts: Counter[str] = Counter()
    total_items = 0
    kept_items = 0
    rejected_items = 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_file = output_path.open("w", encoding="utf-8")

    reject_file = None
    if args.reject_output:
        reject_path = Path(args.reject_output)
        reject_path.parent.mkdir(parents=True, exist_ok=True)
        reject_file = reject_path.open("w", encoding="utf-8")

    try:
        for item in _read_jsonl(Path(args.input)):
            total_items += 1
            keep, reasons = evaluate_item(item, config)
            if keep:
                kept_items += 1
                output_file.write(json.dumps(item, ensure_ascii=False) + "\n")
                continue

            rejected_items += 1
            reason_counts.update(reasons)
            if reject_file:
                rejected_item = dict(item)
                rejected_item["reasons"] = reasons
                reject_file.write(
                    json.dumps(rejected_item, ensure_ascii=False) + "\n"
                )
    finally:
        output_file.close()
        if reject_file:
            reject_file.close()

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "total": total_items,
            "kept": kept_items,
            "rejected": rejected_items,
            "reason_counts": dict(reason_counts),
        }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
