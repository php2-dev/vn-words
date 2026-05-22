from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"Skipping line {line_number}: {exc}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a JSONL file into a delimited txt file."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_pos.jsonl",
        help="Input JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_pos.txt",
        help="Output txt file.",
    )
    parser.add_argument(
        "--fields",
        default="title,pos,definitions",
        help="Comma-separated fields to export in order.",
    )
    parser.add_argument(
        "--sep",
        default="\t",
        help="Field separator (supports \\t and \\n escapes).",
    )
    parser.add_argument(
        "--def-sep",
        default=" | ",
        help="Separator for list values like definitions.",
    )
    return parser.parse_args()


def decode_escapes(value: str) -> str:
    try:
        return value.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def stringify(value: object, list_sep: str) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return list_sep.join(str(item) for item in value)
    return str(value)


def main() -> int:
    args = parse_args()
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]
    if not fields:
        print("No fields provided via --fields.", file=sys.stderr)
        return 2

    sep = decode_escapes(args.sep)
    def_sep = decode_escapes(args.def_sep)

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        for item in read_jsonl(input_path):
            row = [stringify(item.get(field), def_sep) for field in fields]
            output_file.write(sep.join(row))
            output_file.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
