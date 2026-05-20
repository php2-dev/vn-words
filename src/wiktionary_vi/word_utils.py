from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Sequence, Set

VIETNAMESE_LETTERS = (
    "a-zA-Z"
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵ"
    "đ"
)

WORD_RE = re.compile(
    rf"^[{VIETNAMESE_LETTERS}]+(?:[ -][{VIETNAMESE_LETTERS}]+)*$",
    re.IGNORECASE,
)

VOWEL_RE = re.compile(
    r"[aăâeêioôơuưyàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệ"
    r"ìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)

COMBINING_MARK_RE = re.compile(r"[\u0300-\u036f]")
SPACE_RE = re.compile(r"\s+")


def normalize_spaces(text: str) -> str:
    return SPACE_RE.sub(" ", text.strip())


def normalize_word(word: str) -> str:
    return normalize_spaces(word).lower()


def strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    stripped = COMBINING_MARK_RE.sub("", normalized)
    return stripped.replace("đ", "d").replace("Đ", "D")


def split_syllables(word: str) -> List[str]:
    normalized = normalize_word(word).replace("-", " ")
    return [part for part in normalized.split(" ") if part]


def count_syllables(word: str) -> int:
    return len(split_syllables(word))


def has_vietnamese_shape(word: str) -> bool:
    return bool(WORD_RE.match(normalize_spaces(word)))


def has_vowel_like_sound(syllable: str) -> bool:
    return bool(VOWEL_RE.search(syllable))


def load_word_set(path: str) -> Set[str]:
    words: Set[str] = set()
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(normalize_word(line))
    return words


def merge_word_sets(*sets: Iterable[str]) -> Set[str]:
    merged: Set[str] = set()
    for values in sets:
        for value in values:
            normalized = normalize_word(value)
            if normalized:
                merged.add(normalized)
    return merged


def contains_any(text: str, needles: Sequence[str]) -> bool:
    normalized = normalize_word(text)
    return any(needle in normalized for needle in needles)
