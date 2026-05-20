from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select top-ranked words from a scored JSONL file."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_scored.jsonl",
        help="Input scored JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_selected.jsonl",
        help="Output JSONL file.",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "txt", "csv"],
        default="jsonl",
        help="Output format.",
    )
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--min-score", type=float, default=0.78)
    parser.add_argument(
        "--pos",
        nargs="*",
        choices=["noun", "verb", "adjective"],
        default=None,
        help="Optional POS filter.",
    )
    parser.add_argument(
        "--exclude-flags",
        nargs="*",
        default=[
            "concrete_object_definition",
            "dry_domain_definition",
            "negative_definition",
            "technical_or_meta_definition",
            "mostly_sino_vietnamese",
            "loanword_marker",
            "loanword_definition",
            "likely_transliteration",
        ],
        help="Flags that disqualify a word.",
    )
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Allow rows marked rejected.",
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


def _passes(
    item: Dict[str, object],
    min_score: float,
    pos: Sequence[str] | None,
    exclude_flags: Sequence[str],
    include_rejected: bool,
) -> bool:
    if not include_rejected and item.get("rejected"):
        return False

    if pos and item.get("pos") not in pos:
        return False

    if _overall(item) < min_score:
        return False

    flags = item.get("flags", [])
    if not isinstance(flags, list):
        flags = []
    if set(str(flag) for flag in flags) & set(exclude_flags):
        return False

    return True


def _write_jsonl(path: Path, items: Sequence[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def _write_txt(path: Path, items: Sequence[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(f"{item.get('title', '')}\n")


def _csv_cell(value: object) -> str:
    text = str(value).replace('"', '""')
    return f'"{text}"'


def _write_csv(path: Path, items: Sequence[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        file.write("title,pos,overall,clean,pleasant,readable,native_vi,frequency,flags\n")
        for item in items:
            scores = item.get("scores", {})
            if not isinstance(scores, dict):
                scores = {}
            flags = item.get("flags", [])
            if not isinstance(flags, list):
                flags = []
            row = [
                item.get("title", ""),
                item.get("pos", ""),
                scores.get("overall", ""),
                scores.get("clean", ""),
                scores.get("pleasant", ""),
                scores.get("readable", ""),
                scores.get("native_vi", ""),
                scores.get("frequency", ""),
                "|".join(str(flag) for flag in flags),
            ]
            file.write(",".join(_csv_cell(cell) for cell in row) + "\n")


def main() -> None:
    args = parse_args()
    candidates: List[Dict[str, object]] = []
    for item in read_jsonl(Path(args.input)):
        if _passes(
            item,
            min_score=args.min_score,
            pos=args.pos,
            exclude_flags=args.exclude_flags,
            include_rejected=args.include_rejected,
        ):
            candidates.append(item)

    candidates.sort(
        key=lambda item: (
            _overall(item),
            float(item.get("scores", {}).get("pleasant", 0.0))
            if isinstance(item.get("scores"), dict)
            else 0.0,
            str(item.get("title", "")),
        ),
        reverse=True,
    )
    selected = candidates[: args.limit]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "jsonl":
        _write_jsonl(output_path, selected)
    elif args.format == "txt":
        _write_txt(output_path, selected)
    else:
        _write_csv(output_path, selected)


if __name__ == "__main__":
    main()
