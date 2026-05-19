from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from .api import get_category_members, get_page_wikitext
from .parser import extract_pos_definitions

CATEGORIES = {
    "noun": "Thể loại:Danh từ tiếng Việt",
    "verb": "Thể loại:Động từ tiếng Việt",
    "adjective": "Thể loại:Tính từ tiếng Việt",
}


def _source_url(title: str) -> str:
    return f"https://vi.wiktionary.org/wiki/{title.replace(' ', '_')}"


def _log(message: str) -> None:
    print(message, flush=True)


def iter_items(
    limit_per_category: Optional[int] = None,
    sleep_seconds: float = 0.1,
    log_every: int = 200,
    verbose: bool = True,
) -> Iterator[Dict[str, object]]:
    total_seen = 0
    total_kept = 0

    for pos_key, category in CATEGORIES.items():
        seen = 0
        kept = 0
        if verbose:
            _log(f"[{pos_key}] start {category}")
        for title in get_category_members(category, limit=limit_per_category):
            seen += 1
            total_seen += 1
            wikitext = get_page_wikitext(title)
            if not wikitext:
                continue

            definitions = extract_pos_definitions(wikitext).get(pos_key, [])
            if not definitions:
                continue

            kept += 1
            total_kept += 1
            yield {
                "title": title,
                "pos": pos_key,
                "definitions": definitions,
                "source_url": _source_url(title),
            }

            if verbose and log_every > 0 and seen % log_every == 0:
                _log(
                    f"[{pos_key}] seen {seen} kept {kept} | total seen {total_seen} kept {total_kept}"
                )

            if sleep_seconds:
                time.sleep(sleep_seconds)

        if verbose:
            _log(f"[{pos_key}] done seen {seen} kept {kept}")

    if verbose:
        _log(f"[total] seen {total_seen} kept {total_kept}")


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
    log_every: int = 200,
    verbose: bool = True,
) -> None:
    items = iter_items(
        limit_per_category=limit_per_category,
        sleep_seconds=sleep_seconds,
        log_every=log_every,
        verbose=verbose,
    )

    if fmt == "jsonl":
        write_jsonl(output_path, items)
        return

    if fmt == "csv":
        write_csv(output_path, items)
        return

    raise ValueError(f"Unsupported format: {fmt}")
