from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .api import get_category_members, get_page_wikitext
from .parser import extract_pos_definitions

CATEGORIES = {
    "noun": "Thể loại:Danh từ tiếng Việt",
    "verb": "Thể loại:Động từ tiếng Việt",
    "adjective": "Thể loại:Tính từ tiếng Việt",
}


def _source_url(title: str) -> str:
    return f"https://vi.wiktionary.org/wiki/{title.replace(' ', '_')}"


def collect_items(
    limit_per_category: Optional[int] = None,
    sleep_seconds: float = 0.1,
) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []

    for pos_key, category in CATEGORIES.items():
        for title in get_category_members(category, limit=limit_per_category):
            wikitext = get_page_wikitext(title)
            if not wikitext:
                continue

            definitions = extract_pos_definitions(wikitext).get(pos_key, [])
            if not definitions:
                continue

            items.append(
                {
                    "title": title,
                    "pos": pos_key,
                    "definitions": definitions,
                    "source_url": _source_url(title),
                }
            )

            if sleep_seconds:
                time.sleep(sleep_seconds)

    return items


def write_jsonl(output_path: Path, items: Iterable[Dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_csv(output_path: Path, items: Iterable[Dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["title", "pos", "definitions", "source_url"]
        )
        writer.writeheader()
        for item in items:
            definitions = " | ".join(item["definitions"])
            writer.writerow(
                {
                    "title": item["title"],
                    "pos": item["pos"],
                    "definitions": definitions,
                    "source_url": item["source_url"],
                }
            )


def run(
    output_path: Path,
    fmt: str = "jsonl",
    limit_per_category: Optional[int] = None,
    sleep_seconds: float = 0.1,
) -> None:
    items = collect_items(
        limit_per_category=limit_per_category, sleep_seconds=sleep_seconds
    )

    if fmt == "jsonl":
        write_jsonl(output_path, items)
        return

    if fmt == "csv":
        write_csv(output_path, items)
        return

    raise ValueError(f"Unsupported format: {fmt}")
