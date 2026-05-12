from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import mwparserfromhell

_POS_TITLES = {
    "Danh từ": "noun",
    "Động từ": "verb",
    "Tính từ": "adjective",
}

_POS_TEMPLATES = {
    "noun": "noun",
    "verb": "verb",
    "adj": "adjective",
    "adjective": "adjective",
}

_VIE_LANG_TEMPLATES = {"vie", "vi"}

_HEADING_RE = re.compile(r"^(=+)\s*(.+?)\s*\1\s*$")
_DEF_RE = re.compile(r"^(#+)(?![:*])\s*(.+)$")
_TEMPLATE_RE = re.compile(r"^\{\{\s*-\s*(.+?)\s*-\s*\}\}\s*$")


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

    cleaned = mwparserfromhell.parse(text).strip_code().strip()
    return cleaned or None


def _parse_template_heading(line: str) -> Optional[str]:
    match = _TEMPLATE_RE.match(line.strip())
    if not match:
        return None
    name = match.group(1).strip().lower().replace("_", " ")
    name = re.sub(r"\s+", " ", name)
    return name


def _is_language_template(name: str) -> bool:
    if name in _VIE_LANG_TEMPLATES:
        return False
    if name in _POS_TEMPLATES:
        return False
    return len(name) <= 3


def extract_vietnamese_section(wikitext: str) -> Optional[str]:
    lines = wikitext.splitlines()
    in_vi = False
    buffer: List[str] = []

    for line in lines:
        heading = _parse_heading(line)
        if heading and heading[0] == 2:
            if in_vi:
                break
            if heading[1] == "Tiếng Việt":
                in_vi = True
            continue

        template = _parse_template_heading(line)
        if template:
            if template in _VIE_LANG_TEMPLATES:
                in_vi = True
                continue
            if in_vi and _is_language_template(template):
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
                current_pos = _POS_TITLES.get(title)
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
