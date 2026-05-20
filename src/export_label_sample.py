from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
from typing import Dict, Iterable, List


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a stratified CSV sample for human/LLM word scoring labels."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_scored.jsonl",
        help="Input scored JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/word_label_sample.csv",
        help="Output CSV label file.",
    )
    parser.add_argument("--size", type=int, default=600)
    parser.add_argument("--top-size", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Include rejected rows in the sampling pool.",
    )
    return parser.parse_args()


def _overall(item: Dict[str, object]) -> float:
    scores = item.get("scores")
    if not isinstance(scores, dict):
        return 0.0
    try:
        return float(scores.get("overall", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _bucket(score: float) -> str:
    if score >= 0.88:
        return "excellent"
    if score >= 0.82:
        return "high"
    if score >= 0.74:
        return "medium"
    return "low"


def _definition(item: Dict[str, object]) -> str:
    definitions = item.get("definitions")
    if not isinstance(definitions, list):
        return ""
    return " | ".join(str(value) for value in definitions)


def _flags(item: Dict[str, object]) -> str:
    flags = item.get("flags")
    if not isinstance(flags, list):
        return ""
    return "|".join(str(flag) for flag in flags)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    items = [
        item
        for item in read_jsonl(Path(args.input))
        if args.include_rejected or not item.get("rejected")
    ]
    items.sort(key=_overall, reverse=True)

    selected: Dict[tuple[str, str], Dict[str, object]] = {}
    for item in items[: args.top_size]:
        selected[(str(item.get("title", "")), str(item.get("pos", "")))] = item

    buckets: Dict[str, List[Dict[str, object]]] = {
        "excellent": [],
        "high": [],
        "medium": [],
        "low": [],
    }
    for item in items:
        buckets[_bucket(_overall(item))].append(item)

    remaining = max(0, args.size - len(selected))
    per_bucket = max(1, remaining // len(buckets))
    for bucket_items in buckets.values():
        rng.shuffle(bucket_items)
        for item in bucket_items[:per_bucket]:
            selected[(str(item.get("title", "")), str(item.get("pos", "")))] = item

    if len(selected) < args.size:
        shuffled = list(items)
        rng.shuffle(shuffled)
        for item in shuffled:
            selected[(str(item.get("title", "")), str(item.get("pos", "")))] = item
            if len(selected) >= args.size:
                break

    rows = sorted(selected.values(), key=_overall, reverse=True)[: args.size]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "title",
                "pos",
                "overall",
                "clean",
                "pleasant",
                "readable",
                "native_vi",
                "frequency",
                "flags",
                "definitions",
                "label_keep",
                "label_pleasant",
                "label_readable",
                "label_native_vi",
                "label_note",
            ],
        )
        writer.writeheader()
        for item in rows:
            scores = item.get("scores", {})
            if not isinstance(scores, dict):
                scores = {}
            writer.writerow(
                {
                    "title": item.get("title", ""),
                    "pos": item.get("pos", ""),
                    "overall": scores.get("overall", ""),
                    "clean": scores.get("clean", ""),
                    "pleasant": scores.get("pleasant", ""),
                    "readable": scores.get("readable", ""),
                    "native_vi": scores.get("native_vi", ""),
                    "frequency": scores.get("frequency", ""),
                    "flags": _flags(item),
                    "definitions": _definition(item),
                    "label_keep": "",
                    "label_pleasant": "",
                    "label_readable": "",
                    "label_native_vi": "",
                    "label_note": "",
                }
            )


if __name__ == "__main__":
    main()
