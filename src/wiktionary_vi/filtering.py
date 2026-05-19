from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Dict, Iterable, List, Optional, Tuple

VIET_WORD_RE = re.compile(
    r"^[A-Za-zÀ-ỹĐđ]+(?: [A-Za-zÀ-ỹĐđ]+)*$", re.UNICODE
)

DEFAULT_STOP_PHRASES = (
    "viết tắt",
    "từ viết tắt",
    "viết tắt của",
    "ký hiệu",
    "chữ cái",
    "đơn vị",
    "tên riêng",
    "tên hóa học",
    "tên hoá học",
    "tên khoa học",
    "thuật ngữ",
    "phiên âm",
    "tiếng lóng",
)


@dataclass
class FilterConfig:
    min_length: int = 2
    max_length: int = 12
    require_lowercase: bool = True
    stop_phrases: Tuple[str, ...] = DEFAULT_STOP_PHRASES
    freq_min: Optional[float] = None
    freq_map: Optional[Dict[str, float]] = None
    require_freq: bool = False


def load_frequency_file(path: Path) -> Dict[str, float]:
    freq_map: Dict[str, float] = {}
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            word: str
            freq: float

            if "\t" in line:
                parts = [p.strip() for p in line.split("\t") if p.strip()]
            elif "," in line:
                parts = [p.strip() for p in line.split(",") if p.strip()]
            else:
                parts = [line]

            word = parts[0].strip()
            if not word:
                continue

            if len(parts) >= 2:
                try:
                    freq = float(parts[1])
                except ValueError:
                    freq = 0.0
            else:
                freq = 1.0

            word_key = word.lower()
            if word_key in freq_map:
                freq_map[word_key] = max(freq_map[word_key], freq)
            else:
                freq_map[word_key] = freq

    return freq_map


def load_stop_phrases(path: Path) -> Tuple[str, ...]:
    phrases: List[str] = []
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            phrases.append(line.lower())
    return tuple(phrases)


def _normalize_word(word: str) -> str:
    return word.strip().lower()


def _has_stop_phrase(definitions: Iterable[str], phrases: Tuple[str, ...]) -> bool:
    text = " ".join(definitions).lower()
    return any(phrase in text for phrase in phrases)


def evaluate_item(item: Dict[str, object], config: FilterConfig) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    title = str(item.get("title", "")).strip()
    definitions = item.get("definitions")

    if not title:
        reasons.append("empty_title")
        return False, reasons

    if any(char.isdigit() for char in title):
        reasons.append("contains_digit")

    if "-" in title or "_" in title:
        reasons.append("contains_separator")

    if config.require_lowercase and title != title.lower():
        reasons.append("not_lowercase")

    if not VIET_WORD_RE.match(title):
        reasons.append("non_vietnamese_chars")

    if len(title) < config.min_length:
        reasons.append("too_short")

    if len(title) > config.max_length:
        reasons.append("too_long")

    if isinstance(definitions, list) and definitions:
        if _has_stop_phrase(definitions, config.stop_phrases):
            reasons.append("stop_phrase")

    if config.freq_map is not None:
        freq = config.freq_map.get(_normalize_word(title))
        if config.freq_min is not None:
            if (freq or 0.0) < config.freq_min:
                reasons.append("low_frequency")
        elif config.require_freq and freq is None:
            reasons.append("missing_frequency")
    elif config.require_freq:
        reasons.append("missing_frequency")

    return len(reasons) == 0, reasons


def write_jsonl(path: Path, items: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")
