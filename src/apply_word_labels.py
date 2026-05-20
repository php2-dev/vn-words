from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

from wiktionary_vi.scoring import ScoreWeights, weighted_overall


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply human/LLM CSV labels to scored word JSONL."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_scored.jsonl",
        help="Input scored JSONL file.",
    )
    parser.add_argument(
        "--labels",
        default="data/word_label_sample.csv",
        help="CSV labels exported by export_label_sample.py.",
    )
    parser.add_argument(
        "--output",
        default="data/vi_wiktionary_calibrated.jsonl",
        help="Output calibrated JSONL file.",
    )
    parser.add_argument(
        "--blend",
        type=float,
        default=0.75,
        help="How strongly labels override heuristic component scores.",
    )
    return parser.parse_args()


def _parse_score(value: str) -> Optional[float]:
    text = value.strip()
    if not text:
        return None
    try:
        score = float(text)
    except ValueError:
        return None
    if score > 1.0:
        score = score / 5.0
    return max(0.0, min(1.0, score))


def _parse_keep(value: str) -> Optional[bool]:
    text = value.strip().lower()
    if not text:
        return None
    if text in {"1", "yes", "y", "true", "keep", "giữ", "giu"}:
        return True
    if text in {"0", "no", "n", "false", "drop", "loại", "loai", "reject"}:
        return False
    return None


def load_labels(path: Path) -> Dict[tuple[str, str], Dict[str, str]]:
    labels: Dict[tuple[str, str], Dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            title = row.get("title", "").strip()
            pos = row.get("pos", "").strip()
            if title and pos:
                labels[(title, pos)] = row
    return labels


def _blend_score(original: float, label: Optional[float], blend: float) -> float:
    if label is None:
        return original
    return round(original * (1.0 - blend) + label * blend, 4)


def apply_label(
    item: Dict[str, object],
    label: Mapping[str, str],
    blend: float,
) -> Dict[str, object]:
    scores = item.get("scores")
    if not isinstance(scores, dict):
        return item

    updated_scores = dict(scores)
    for field, label_field in (
        ("pleasant", "label_pleasant"),
        ("readable", "label_readable"),
        ("native_vi", "label_native_vi"),
    ):
        try:
            original = float(updated_scores.get(field, 0.0))
        except (TypeError, ValueError):
            original = 0.0
        updated_scores[field] = _blend_score(
            original,
            _parse_score(label.get(label_field, "")),
            blend,
        )

    updated_scores["overall"] = weighted_overall(updated_scores, ScoreWeights())
    keep = _parse_keep(label.get("label_keep", ""))

    updated = dict(item)
    flags = item.get("flags", [])
    if not isinstance(flags, list):
        flags = []
    updated_flags = list(flags)
    if keep is False and "manual_reject" not in updated_flags:
        updated_flags.append("manual_reject")
        updated_scores["overall"] = min(float(updated_scores["overall"]), 0.30)
        updated["rejected"] = True
    elif keep is True:
        updated["rejected"] = False
        if "manual_keep" not in updated_flags:
            updated_flags.append("manual_keep")

    note = label.get("label_note", "").strip()
    if note:
        updated["label_note"] = note

    updated["scores"] = updated_scores
    updated["flags"] = sorted(updated_flags)
    return updated


def main() -> None:
    args = parse_args()
    labels = load_labels(Path(args.labels))
    blend = max(0.0, min(1.0, args.blend))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for item in read_jsonl(Path(args.input)):
            key = (str(item.get("title", "")), str(item.get("pos", "")))
            label = labels.get(key)
            if label is not None:
                item = apply_label(item, label, blend)
            output_file.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
