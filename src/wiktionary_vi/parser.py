from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import mwparserfromhell

_POS_TITLES = {
    "Danh từ": "noun",
    "Danh từ tiếng Việt": "noun",
    "Động từ": "verb",
    "Động từ tiếng Việt": "verb",
    "Tính từ": "adjective",
    "Tính từ tiếng Việt": "adjective",
}

_POS_TEMPLATES = {
    "n": "noun",
    "noun": "noun",
    "vie noun": "noun",
    "vi noun": "noun",
    "vie-noun": "noun",
    "vi-noun": "noun",
    "danh từ": "noun",
    "dt": "noun",
    "v": "verb",
    "verb": "verb",
    "vie verb": "verb",
    "vi verb": "verb",
    "vie-verb": "verb",
    "vi-verb": "verb",
    "động từ": "verb",
    "đt": "verb",
    "adj": "adjective",
    "adjc": "adjective",
    "adjective": "adjective",
    "vie adj": "adjective",
    "vi adj": "adjective",
    "vie-adj": "adjective",
    "vi-adj": "adjective",
    "tính từ": "adjective",
    "tt": "adjective",
}

_VIE_LANG_TEMPLATES = {"vie", "vi"}

_HEADING_RE = re.compile(r"^(=+)\s*(.+?)\s*\1\s*$")
_DEF_RE = re.compile(r"^(#+)(?![:*])\s*(.+)$")
_TEMPLATE_RE = re.compile(r"^\{\{\s*(.+?)\s*\}\}\s*$")

_SECTION_TEMPLATE_ALIASES = {
    "etym": "etymology",
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "pron": "pronunciation",
    "ref": "references",
    "rel": "related",
    "trans": "translations",
}

_NON_LANGUAGE_SECTION_TEMPLATES = {
    "etymology",
    "hanviet",
    "hanviet-t",
    "info",
    "nôm",
    "nom",
    "pron",
    "pronunciation",
    "ref",
    "references",
    "rel",
    "related",
    "see also",
    "trans",
    "translations",
    "vie-m",
}


def _parse_heading(line: str) -> Optional[Tuple[int, str]]:
    match = _HEADING_RE.match(line)
    if not match:
        return None
    level = len(match.group(1))
    title = match.group(2).strip()
    return level, title


def _clean_definition_line(line: str) -> Optional[str]:
    match = _DEF_RE.match(line)
    if not match:
        return None

    text = match.group(2).strip()
    if not text:
        return None

    text = _expand_definition_templates(text)
    cleaned = mwparserfromhell.parse(text).strip_code().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or None


def _split_template_args(raw_args: str) -> List[str]:
    return [
        part.split("=", 1)[-1].strip()
        for part in raw_args.split("|")
        if part.strip()
    ]


def _expand_definition_templates(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = _normalize_template_name(match.group(1))
        args = _split_template_args(match.group(2))

        if name in {"context", "lb", "label"}:
            labels = [arg for arg in args if arg.lower() not in _VIE_LANG_TEMPLATES]
            return f"({', '.join(labels)})" if labels else ""

        if name in {"see-entry", "like-entry"} and args:
            return f"Xem {args[0]}"

        if name in {
            "alternative form of",
            "alternative spelling of",
            "alt form",
            "vi-alternative spelling of",
        } and args:
            term = (
                args[1]
                if args and args[0].lower() in _VIE_LANG_TEMPLATES and len(args) > 1
                else args[0]
            )
            return f"Dạng thay thế của {term}"

        return match.group(0)

    return re.sub(r"\{\{\s*([^{}|]+)\s*((?:\|[^{}]*)*)\}\}", replace, text)


def _normalize_template_name(name: str) -> str:
    name = name.strip().strip("-").strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", name)


def _normalize_template_arg(value: str) -> str:
    value = value.strip().strip("-").strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", value)


def _parse_template(text: str) -> Optional[Tuple[str, List[str]]]:
    match = _TEMPLATE_RE.match(text.strip())
    if not match:
        return None

    parts = [part.strip() for part in match.group(1).split("|")]
    if not parts:
        return None

    name = _normalize_template_name(parts[0])
    args = [_normalize_template_arg(part.split("=", 1)[-1]) for part in parts[1:]]
    return name, args


def _parse_template_heading(line: str) -> Optional[str]:
    template = _parse_template(line)
    if not template:
        return None
    name, args = template
    if name == "đm" and args:
        return _SECTION_TEMPLATE_ALIASES.get(args[0], args[0])
    if name == "langname" and args:
        return args[0]
    return name


def _parse_templated_heading_title(title: str) -> Optional[str]:
    template = _parse_template(title)
    if not template:
        return None
    name, args = template
    if name == "đm" and args:
        return _SECTION_TEMPLATE_ALIASES.get(args[0], args[0])
    if name == "langname" and args:
        return args[0]
    return name


def _is_language_template(name: str) -> bool:
    if name in _VIE_LANG_TEMPLATES:
        return False
    if name in _POS_TEMPLATES:
        return False
    if name in _NON_LANGUAGE_SECTION_TEMPLATES:
        return False
    return len(name) <= 3


def _heading_pos(title: str) -> Optional[str]:
    normalized_title = title.strip()
    pos = _POS_TITLES.get(normalized_title)
    if pos:
        return pos

    template_title = _parse_templated_heading_title(normalized_title)
    if template_title:
        return _POS_TEMPLATES.get(template_title)

    return _POS_TEMPLATES.get(_normalize_template_arg(normalized_title))


def extract_vietnamese_section(wikitext: str) -> Optional[str]:
    lines = wikitext.splitlines()
    in_vi = False
    buffer: List[str] = []

    for line in lines:
        heading = _parse_heading(line)
        if heading and heading[0] == 2:
            if in_vi:
                break
            template_title = _parse_templated_heading_title(heading[1])
            if heading[1] == "Tiếng Việt" or template_title in _VIE_LANG_TEMPLATES:
                in_vi = True
            continue

        template = _parse_template_heading(line)
        if template:
            if template in _VIE_LANG_TEMPLATES:
                in_vi = True
                continue
            if in_vi and line.strip().startswith("{{-") and _is_language_template(template):
                break

        if in_vi:
            buffer.append(line)

    if not buffer:
        return None

    return "\n".join(buffer)


def extract_pos_definitions(wikitext: str) -> Dict[str, List[str]]:
    section = extract_vietnamese_section(wikitext)
    results = {"noun": [], "verb": [], "adjective": []}

    if not section:
        return results

    current_pos: Optional[str] = None

    for line in section.splitlines():
        heading = _parse_heading(line)
        if heading:
            level, title = heading
            if level == 3:
                current_pos = _heading_pos(title)
            elif level <= 2:
                current_pos = None
            continue

        template = _parse_template_heading(line)
        if template:
            pos = _POS_TEMPLATES.get(template)
            if pos:
                current_pos = pos
            continue

        if not current_pos:
            continue

        definition = _clean_definition_line(line)
        if definition:
            results[current_pos].append(definition)

    return results
