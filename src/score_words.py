from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping

from wiktionary_vi.filtering import load_frequency_file
from wiktionary_vi.scoring import ScoreWeights, build_config, score_items


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score Vietnamese Wiktionary words for clean, readable, pleasant names."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_pos.jsonl",
        help="Input JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_scored.jsonl",
        help="Output scored JSONL file.",
    )
    parser.add_argument(
        "--report",
        default="data/vi_wiktionary_scoring_report.json",
        help="Output JSON report path. Use empty string to disable.",
    )
    parser.add_argument("--freq-file", default=None, help="Optional frequency file.")
    parser.add_argument("--profanity-file", default=None)
    parser.add_argument("--sino-file", default=None)
    parser.add_argument("--loanword-file", default=None)
    parser.add_argument("--weight-clean", type=float, default=0.20)
    parser.add_argument("--weight-pleasant", type=float, default=0.35)
    parser.add_argument("--weight-readable", type=float, default=0.20)
    parser.add_argument("--weight-native-vi", type=float, default=0.15)
    parser.add_argument("--weight-frequency", type=float, default=0.10)
    parser.add_argument(
        "--keep-rejected",
        action="store_true",
        help="Keep rejected rows in the main output instead of writing only candidates.",
    )
    return parser.parse_args()


def _path_or_none(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)


def write_report(
    path: Path,
    total: int,
    written: int,
    rejected: int,
    flag_counts: Mapping[str, int],
    score_buckets: Mapping[str, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total": total,
        "written": written,
        "rejected": rejected,
        "flag_counts": dict(flag_counts),
        "overall_score_buckets": dict(score_buckets),
    }
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    frequency = None
    if args.freq_file:
        frequency = load_frequency_file(Path(args.freq_file))

    weights = ScoreWeights(
        clean=args.weight_clean,
        pleasant=args.weight_pleasant,
        readable=args.weight_readable,
        native_vi=args.weight_native_vi,
        frequency=args.weight_frequency,
    )
    config = build_config(
        profanity_file=_path_or_none(args.profanity_file),
        sino_file=_path_or_none(args.sino_file),
        loanword_file=_path_or_none(args.loanword_file),
        frequency=frequency,
        weights=weights,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    written = 0
    rejected = 0
    flag_counts: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()

    with output_path.open("w", encoding="utf-8") as output_file:
        for scored in score_items(read_jsonl(Path(args.input)), config):
            total += 1
            flags = scored.get("flags")
            if isinstance(flags, list):
                flag_counts.update(str(flag) for flag in flags)

            scores = scored.get("scores", {})
            overall = scores.get("overall", 0.0) if isinstance(scores, dict) else 0.0
            bucket = f"{int(float(overall) * 10) / 10:.1f}"
            score_buckets[bucket] += 1

            if scored.get("rejected"):
                rejected += 1
                if not args.keep_rejected:
                    continue

            written += 1
            output_file.write(json.dumps(scored, ensure_ascii=False) + "\n")

    if args.report:
        write_report(
            Path(args.report),
            total=total,
            written=written,
            rejected=rejected,
            flag_counts=flag_counts,
            score_buckets=score_buckets,
        )


if __name__ == "__main__":
    main()
