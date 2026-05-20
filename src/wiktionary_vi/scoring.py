from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from wiktionary_vi.word_utils import (
    count_syllables,
    has_vietnamese_shape,
    has_vowel_like_sound,
    load_word_set,
    normalize_word,
    split_syllables,
    strip_diacritics,
)

DEFAULT_PROFANITY = {
    "buồi",
    "cặc",
    "cứt",
    "đái",
    "đéo",
    "đĩ",
    "địt",
    "ỉa",
    "lồn",
    "nứng",
    "vãi",
}

DEFAULT_LOANWORD_MARKERS = {
    "a xít",
    "a-xít",
    "axit",
    "bê tông",
    "cà phê",
    "căng tin",
    "cát sét",
    "công ten nơ",
    "ga ra",
    "gác đờ bu",
    "in tơ nét",
    "ki lô",
    "mít tinh",
    "ô tô",
    "ra đa",
    "sô cô la",
    "xà phòng",
}

DEFAULT_SINO_SYLLABLES = {
    "ác",
    "an",
    "anh",
    "bạch",
    "bản",
    "bảo",
    "bất",
    "bình",
    "cao",
    "chính",
    "chỉ",
    "chủ",
    "chứng",
    "công",
    "cộng",
    "cơ",
    "cổ",
    "cường",
    "danh",
    "dân",
    "đại",
    "đạo",
    "địa",
    "điện",
    "định",
    "độc",
    "đức",
    "gia",
    "giáo",
    "hạ",
    "hải",
    "hành",
    "hậu",
    "hiện",
    "hiệp",
    "hiệu",
    "hình",
    "hóa",
    "hoá",
    "hoàng",
    "học",
    "hợp",
    "hữu",
    "khoa",
    "khí",
    "kiến",
    "kinh",
    "kỹ",
    "lâm",
    "lập",
    "lễ",
    "liên",
    "linh",
    "luật",
    "lực",
    "minh",
    "mỹ",
    "nam",
    "nghiệp",
    "nghĩa",
    "ngọc",
    "ngôn",
    "nguyên",
    "nhân",
    "nhiên",
    "nội",
    "pháp",
    "phẩm",
    "phân",
    "phi",
    "phong",
    "phú",
    "phúc",
    "phương",
    "quân",
    "quốc",
    "quyền",
    "sản",
    "sinh",
    "sự",
    "tác",
    "tâm",
    "tân",
    "tế",
    "thái",
    "thần",
    "thể",
    "thiên",
    "thiện",
    "thống",
    "thực",
    "thủy",
    "thuỷ",
    "tiền",
    "tiểu",
    "tín",
    "tinh",
    "tổ",
    "tôn",
    "trí",
    "trọng",
    "trung",
    "tự",
    "tư",
    "văn",
    "vật",
    "viên",
    "việt",
    "vô",
    "xã",
    "xuất",
}

POSITIVE_MARKERS = {
    "ấm",
    "êm",
    "hiền",
    "lành",
    "mát",
    "mềm",
    "ngọt",
    "sáng",
    "thơm",
    "trong",
    "vui",
    "xanh",
    "yên",
}

NEGATIVE_MARKERS = {
    "ác",
    "bẩn",
    "bệnh",
    "buồn",
    "chết",
    "chửi",
    "đau",
    "độc",
    "giận",
    "giết",
    "hôi",
    "khóc",
    "máu",
    "mù",
    "rác",
    "sợ",
    "thối",
    "xấu",
}

POSITIVE_DEFINITION_MARKERS = {
    "ấm áp",
    "an lành",
    "bình yên",
    "cái đẹp",
    "dễ chịu",
    "dễ nghe",
    "đầm ấm",
    "đẹp",
    "điều hay",
    "êm tai",
    "hạnh phúc",
    "hòa thuận",
    "hoà thuận",
    "may mắn",
    "mùi thơm",
    "thanh bình",
    "tinh khiết",
    "tốt đẹp",
    "tốt lành",
    "vẻ đẹp",
    "vui vẻ",
}

NEGATIVE_DEFINITION_MARKERS = {
    "bất lợi",
    "cái không hay",
    "chết",
    "đàn áp",
    "đau",
    "đe dọa",
    "đe doạ",
    "gái điếm",
    "giết",
    "khó chịu",
    "không hay",
    "lừa",
    "lừa dối",
    "ma túy",
    "ma tuý",
    "nghèo",
    "ngược đãi",
    "nói nhiều",
    "phạm phải",
    "thuốc phiện",
    "thô bạo",
    "thô tục",
    "tục",
    "tội",
    "xấu",
}

DRY_DOMAIN_DEFINITION_MARKERS = {
    "bưu điện",
    "chính trị",
    "cơ quan",
    "công ty",
    "đào tạo",
    "đơn vị",
    "giấy chứng nhận",
    "hóa học",
    "hoá học",
    "hợp đồng",
    "khoa học",
    "kỹ thuật",
    "loại từ",
    "máy tính",
    "nhà thầu",
    "pháp luật",
    "số lượng",
    "thuật ngữ",
    "tổ chức",
    "văn bản",
}

CONCRETE_DEFINITION_STARTS = {
    "cây ",
    "chim ",
    "con ",
    "củ ",
    "dụng cụ ",
    "loài ",
    "loại ",
    "một loài ",
    "một loại ",
    "quả ",
    "rau ",
    "thứ ",
}

CONCRETE_DEFINITION_MARKERS = {
    "có vỏ",
    "dùng làm gia vị",
    "dùng làm thức ăn",
    "họ với",
    "lá dài",
    "mọc bò",
    "sống ở",
    "thân nhỏ",
    "thân cây",
    "thức ăn",
    "trồng trong",
}

TECHNICAL_DEFINITION_MARKERS = {
    "chữ cái",
    "chuyên ngành",
    "đơn vị",
    "hóa học",
    "hoá học",
    "khoa học",
    "ký hiệu",
    "phiên âm",
    "phương ngữ",
    "thuật ngữ",
    "tự mẫu",
    "tên khoa học",
    "tiếng lóng",
    "viết tắt",
}

LOAN_DEFINITION_MARKERS = {
    "gốc anh",
    "gốc pháp",
    "mượn",
    "phiên âm",
    "tiếng anh",
    "tiếng pháp",
}

STRICT_REJECT_FLAGS = {
    "contains_digit",
    "contains_profanity",
    "empty_title",
    "invalid_shape",
    "missing_vowel",
}


@dataclass(frozen=True)
class ScoreWeights:
    clean: float = 0.20
    pleasant: float = 0.35
    readable: float = 0.20
    native_vi: float = 0.15
    frequency: float = 0.10


@dataclass
class ScoringConfig:
    profanity: Set[str] = field(default_factory=lambda: set(DEFAULT_PROFANITY))
    sino_syllables: Set[str] = field(
        default_factory=lambda: set(DEFAULT_SINO_SYLLABLES)
    )
    loanword_markers: Set[str] = field(
        default_factory=lambda: set(DEFAULT_LOANWORD_MARKERS)
    )
    frequency: Optional[Mapping[str, float]] = None
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    min_clean: float = 0.80


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _definitions_text(item: Mapping[str, object]) -> str:
    definitions = item.get("definitions")
    if isinstance(definitions, list):
        return " ".join(str(value) for value in definitions)
    return ""


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def _contains_any_phrase(text: str, phrases: Sequence[str]) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in phrases)


def _load_optional_set(path: Optional[Path]) -> Set[str]:
    if not path:
        return set()
    return load_word_set(str(path))


def build_config(
    profanity_file: Optional[Path] = None,
    sino_file: Optional[Path] = None,
    loanword_file: Optional[Path] = None,
    frequency: Optional[Mapping[str, float]] = None,
    weights: Optional[ScoreWeights] = None,
) -> ScoringConfig:
    profanity = set(DEFAULT_PROFANITY) | _load_optional_set(profanity_file)
    sino = set(DEFAULT_SINO_SYLLABLES) | _load_optional_set(sino_file)
    loanwords = set(DEFAULT_LOANWORD_MARKERS) | _load_optional_set(loanword_file)
    return ScoringConfig(
        profanity=profanity,
        sino_syllables=sino,
        loanword_markers=loanwords,
        frequency=frequency,
        weights=weights or ScoreWeights(),
    )


def score_clean(
    title: str,
    definitions_text: str,
    config: ScoringConfig,
) -> tuple[float, List[str]]:
    word = normalize_word(title)
    no_tone = strip_diacritics(word)
    flags: List[str] = []
    score = 1.0

    if not word:
        return 0.0, ["empty_title"]

    if any(char.isdigit() for char in word):
        flags.append("contains_digit")
        score -= 0.70

    if not has_vietnamese_shape(word):
        flags.append("invalid_shape")
        score -= 0.45

    if any(not has_vowel_like_sound(s) for s in split_syllables(word)):
        flags.append("missing_vowel")
        score -= 0.35

    profanity_forms = config.profanity | {strip_diacritics(w) for w in config.profanity}
    haystack = f"{word} {no_tone}"
    if any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in profanity_forms):
        flags.append("contains_profanity")
        score = min(score, 0.05)

    lowered_definition = normalize_word(definitions_text)
    for marker in TECHNICAL_DEFINITION_MARKERS:
        if marker in lowered_definition:
            flags.append("technical_or_meta_definition")
            score -= 0.12
            break

    return _clamp(score), flags


def score_readable(title: str) -> tuple[float, List[str], Dict[str, object]]:
    word = normalize_word(title)
    syllables = split_syllables(word)
    char_len = len(word)
    syllable_count = len(syllables)
    flags: List[str] = []
    score = 1.0

    if "-" in word:
        flags.append("hyphenated")
        score -= 0.22

    if "_" in word:
        flags.append("contains_underscore")
        score -= 0.35

    if title != title.lower():
        flags.append("has_uppercase")
        score -= 0.18

    if syllable_count == 0:
        score = 0.0
    elif syllable_count == 1:
        score -= 0.04
    elif syllable_count in (2, 3):
        score += 0.02
    elif syllable_count == 4:
        score -= 0.16
        flags.append("many_syllables")
    else:
        score -= 0.30
        flags.append("too_many_syllables")

    if char_len < 2:
        flags.append("too_short")
        score -= 0.50
    elif char_len > 18:
        flags.append("too_long")
        score -= 0.32
    elif char_len > 13:
        flags.append("long_word")
        score -= 0.14

    if any(len(syllable) > 7 for syllable in syllables):
        flags.append("long_syllable")
        score -= 0.12

    if any(not has_vowel_like_sound(syllable) for syllable in syllables):
        flags.append("hard_to_pronounce")
        score -= 0.20

    features = {
        "char_len": char_len,
        "syllable_count": syllable_count,
        "syllables": syllables,
    }
    return _clamp(score), flags, features


def score_native_vi(
    title: str,
    definitions_text: str,
    config: ScoringConfig,
) -> tuple[float, List[str], Dict[str, object]]:
    word = normalize_word(title)
    syllables = split_syllables(word)
    flags: List[str] = []
    score = 1.0

    sino_hits = [s for s in syllables if s in config.sino_syllables]
    sino_ratio = len(sino_hits) / len(syllables) if syllables else 0.0
    if sino_ratio >= 0.75 and len(syllables) >= 2:
        flags.append("mostly_sino_vietnamese")
        score -= 0.34
    elif sino_ratio >= 0.5 and len(syllables) >= 2:
        flags.append("some_sino_vietnamese")
        score -= 0.18
    elif sino_ratio > 0:
        score -= 0.06

    loan_text = f"{word} {_definitions_text({'definitions': [definitions_text]})}"
    normalized_loan_text = normalize_word(loan_text)
    if any(marker in normalized_loan_text for marker in config.loanword_markers):
        flags.append("loanword_marker")
        score -= 0.35

    if "-" in word:
        flags.append("likely_transliteration")
        score -= 0.28

    lowered_definition = normalize_word(definitions_text)
    for marker in LOAN_DEFINITION_MARKERS:
        if marker in lowered_definition:
            flags.append("loanword_definition")
            score -= 0.25
            break

    features = {
        "sino_ratio": round(sino_ratio, 3),
        "sino_hits": sino_hits,
    }
    return _clamp(score), flags, features


def score_pleasant(title: str, definitions_text: str) -> tuple[float, List[str]]:
    word = normalize_word(title)
    text = f"{word} {normalize_word(definitions_text)}"
    syllables = split_syllables(word)
    flags: List[str] = []
    score = 0.44

    positive_hits = sorted({s for s in syllables if s in POSITIVE_MARKERS})
    negative_hits = sorted({s for s in syllables if s in NEGATIVE_MARKERS})

    if positive_hits:
        flags.append("positive_sound_or_meaning")
        score += min(0.16, 0.07 * len(positive_hits))

    if negative_hits:
        flags.append("negative_sound_or_meaning")
        score -= min(0.28, 0.10 * len(negative_hits))

    if _contains_any_phrase(text, tuple(POSITIVE_DEFINITION_MARKERS)):
        flags.append("positive_definition")
        score += 0.12

    if _contains_any_phrase(text, tuple(NEGATIVE_DEFINITION_MARKERS)):
        flags.append("negative_definition")
        score -= 0.26

    if _contains_any_phrase(text, tuple(DRY_DOMAIN_DEFINITION_MARKERS)):
        flags.append("dry_domain_definition")
        score -= 0.08

    normalized_definition = normalize_word(definitions_text)
    if normalized_definition.startswith(tuple(CONCRETE_DEFINITION_STARTS)) or (
        _contains_any_phrase(text, tuple(CONCRETE_DEFINITION_MARKERS))
    ):
        flags.append("concrete_object_definition")
        score -= 0.05

    if len(syllables) == 2:
        first, second = syllables
        if first and second and first[0] == second[0]:
            flags.append("alliterative")
            score += 0.025

    if count_syllables(word) in (2, 3):
        score += 0.025

    return _clamp(score), flags


def score_frequency(
    title: str,
    frequency: Optional[Mapping[str, float]],
) -> tuple[float, List[str], Dict[str, object]]:
    if frequency is None:
        return 0.40, ["missing_frequency_source"], {"frequency": None}

    value = frequency.get(normalize_word(title))
    if value is None:
        return 0.25, ["missing_frequency"], {"frequency": None}

    score = math.log1p(max(0.0, float(value))) / math.log1p(1_000_000.0)
    return _clamp(score), [], {"frequency": value}


def weighted_overall(scores: Mapping[str, float], weights: ScoreWeights) -> float:
    total_weight = (
        weights.clean
        + weights.pleasant
        + weights.readable
        + weights.native_vi
        + weights.frequency
    )
    if total_weight <= 0:
        return 0.0

    value = (
        scores["clean"] * weights.clean
        + scores["pleasant"] * weights.pleasant
        + scores["readable"] * weights.readable
        + scores["native_vi"] * weights.native_vi
        + scores["frequency"] * weights.frequency
    ) / total_weight
    return round(_clamp(value), 4)


def apply_quality_caps(scores: Mapping[str, float], flags: Sequence[str]) -> float:
    overall = weighted_overall(scores, ScoreWeights())
    flag_set = set(flags)

    if "negative_definition" in flag_set:
        overall = min(overall, 0.74)
    if "dry_domain_definition" in flag_set:
        overall = min(overall, 0.78)
    if "concrete_object_definition" in flag_set:
        overall = min(overall, 0.79)
    if "technical_or_meta_definition" in flag_set:
        overall = min(overall, 0.72)
    if "mostly_sino_vietnamese" in flag_set:
        overall = min(overall, 0.80)
    if "loanword_marker" in flag_set or "loanword_definition" in flag_set:
        overall = min(overall, 0.76)
    if "likely_transliteration" in flag_set:
        overall = min(overall, 0.74)

    return round(_clamp(overall), 4)


def score_item(
    item: Mapping[str, object],
    config: ScoringConfig,
) -> Dict[str, object]:
    title = str(item.get("title", "")).strip()
    definitions_text = _definitions_text(item)

    clean, clean_flags = score_clean(title, definitions_text, config)
    readable, readable_flags, readable_features = score_readable(title)
    native_vi, native_flags, native_features = score_native_vi(
        title, definitions_text, config
    )
    pleasant, pleasant_flags = score_pleasant(title, definitions_text)
    frequency_score, frequency_flags, frequency_features = score_frequency(
        title, config.frequency
    )

    scores = {
        "clean": round(clean, 4),
        "pleasant": round(pleasant, 4),
        "readable": round(readable, 4),
        "native_vi": round(native_vi, 4),
        "frequency": round(frequency_score, 4),
    }
    flags = sorted(
        set(clean_flags + readable_flags + native_flags + pleasant_flags + frequency_flags)
    )
    scores["overall"] = weighted_overall(scores, config.weights)
    scores["overall"] = min(scores["overall"], apply_quality_caps(scores, flags))
    rejected = clean < config.min_clean or bool(STRICT_REJECT_FLAGS & set(flags))

    scored = dict(item)
    scored["scores"] = scores
    scored["flags"] = flags
    scored["features"] = {
        **readable_features,
        **native_features,
        **frequency_features,
    }
    scored["rejected"] = rejected
    return scored


def score_items(
    items: Iterable[Mapping[str, object]],
    config: ScoringConfig,
) -> Iterable[Dict[str, object]]:
    for item in items:
        yield score_item(item, config)
