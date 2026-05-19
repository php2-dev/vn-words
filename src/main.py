from __future__ import annotations

import argparse
from pathlib import Path

from wiktionary_vi.pipeline import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect Vietnamese nouns, verbs, and adjectives from Wiktionary."
        )
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_pos.jsonl",
        help="Output file path.",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="Output format.",
    )
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="Maximum pages per POS category.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Sleep between page requests in seconds.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=200,
        help="Log progress every N pages per category (0 to disable).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable progress logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(
        output_path=Path(args.output),
        fmt=args.format,
        limit_per_category=args.limit_per_category,
        sleep_seconds=args.sleep,
        log_every=args.log_every,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
