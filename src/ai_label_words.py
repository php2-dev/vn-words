from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re
import time
from typing import Dict, Iterable, List, Mapping, Optional

import requests


SYSTEM_PROMPT = """Bạn là chuyên gia từ vựng tiếng Việt.
Nhiệm vụ: chấm từ cho một danh sách từ Wiktionary để chọn các từ sạch, hay,
dễ đọc/dễ viết, tự nhiên tiếng Việt, ít Hán Việt hoặc vay mượn.

Rubric:
- label_keep: true nếu từ đáng giữ trong danh sách từ hay; false nếu nên loại.
- label_pleasant: 0-5. 5 = rất đẹp/êm/tích cực/gợi cảm tốt; 3 = bình thường; 0-1 = xấu, thô, tiêu cực, khô kỹ thuật.
- label_readable: 0-5. 5 = ngắn, dễ đọc, dễ viết; 3 = đọc được nhưng không gọn; 0-1 = khó đọc/phiên âm/ký hiệu.
- label_native_vi: 0-5. 5 = rất tự nhiên tiếng Việt; 3 = hơi Hán Việt/vay mượn nhưng phổ biến; 0-1 = nặng Hán Việt, thuật ngữ, phiên âm, vay mượn rõ.

Ưu tiên cao:
- từ 1-3 âm tiết, nghe đẹp, nghĩa tích cực hoặc trung tính dễ chịu
- tính từ/trạng thái/cảm xúc đẹp: trong trẻo, êm ấm, yên vui
- danh từ trừu tượng hoặc hình ảnh đẹp: hương thơm, bình yên

Hạ điểm hoặc loại:
- tục/bậy, nghĩa xấu, bạo lực, bệnh tật, lừa dối, mại dâm, ma túy
- thuật ngữ kỹ thuật/hành chính/khoa học khô
- tên cây/con/đồ vật cụ thể nếu chỉ hay vì định nghĩa có chữ thơm/đẹp
- từ quá Hán Việt, quá cổ, quá trang trọng, hoặc phiên âm nước ngoài
- từ địa phương, chữ cái, viết tắt, ký hiệu

Trả điểm theo cảm nhận người Việt hiện đại, không quá máy móc theo từng chữ trong định nghĩa.
"""


LABEL_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "pos": {"type": "string"},
                    "label_keep": {"type": "boolean"},
                    "label_pleasant": {"type": "integer", "minimum": 0, "maximum": 5},
                    "label_readable": {"type": "integer", "minimum": 0, "maximum": 5},
                    "label_native_vi": {"type": "integer", "minimum": 0, "maximum": 5},
                    "label_note": {"type": "string"},
                },
                "required": [
                    "title",
                    "pos",
                    "label_keep",
                    "label_pleasant",
                    "label_readable",
                    "label_native_vi",
                    "label_note",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["labels"],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use an LLM to label Vietnamese word quality for final review."
    )
    parser.add_argument(
        "--input",
        default="data/vi_wiktionary_scored.jsonl",
        help="Input scored JSONL file.",
    )
    parser.add_argument(
        "--output",
        default="data/word_ai_labels.csv",
        help="Output CSV label file for apply_word_labels.py.",
    )
    parser.add_argument(
        "--cache",
        default="data/word_ai_label_cache.jsonl",
        help="JSONL cache for resumable API calls.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "ollama"],
        default="openai",
        help="Use OpenAI Responses API or a local Ollama server.",
    )
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Local Ollama server URL.",
    )
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--min-score", type=float, default=0.70)
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Allow rows marked rejected.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between API calls.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write no labels; print the first request payload only.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line:
                yield json.loads(line)


def _overall(item: Mapping[str, object]) -> float:
    scores = item.get("scores")
    if not isinstance(scores, dict):
        return 0.0
    try:
        return float(scores.get("overall", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _definitions(item: Mapping[str, object]) -> str:
    definitions = item.get("definitions")
    if not isinstance(definitions, list):
        return ""
    return " | ".join(str(value) for value in definitions)


def _flags(item: Mapping[str, object]) -> str:
    flags = item.get("flags")
    if not isinstance(flags, list):
        return ""
    return "|".join(str(flag) for flag in flags)


def select_items(
    path: Path,
    limit: int,
    min_score: float,
    include_rejected: bool,
) -> List[Dict[str, object]]:
    items = []
    for item in read_jsonl(path):
        if not include_rejected and item.get("rejected"):
            continue
        if _overall(item) < min_score:
            continue
        items.append(item)
    items.sort(key=_overall, reverse=True)
    return items[:limit]


def load_cache(path: Path) -> Dict[tuple[str, str], Dict[str, object]]:
    cached: Dict[tuple[str, str], Dict[str, object]] = {}
    if not path.exists():
        return cached
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            item = json.loads(line)
            key = (str(item.get("title", "")), str(item.get("pos", "")))
            if key[0] and key[1]:
                cached[key] = item
    return cached


def append_cache(path: Path, labels: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for label in labels:
            file.write(json.dumps(label, ensure_ascii=False) + "\n")


def build_user_prompt(batch: List[Mapping[str, object]]) -> str:
    rows = []
    for item in batch:
        scores = item.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}
        rows.append(
            {
                "title": item.get("title", ""),
                "pos": item.get("pos", ""),
                "definitions": _definitions(item),
                "scores": {
                    "overall": scores.get("overall"),
                    "pleasant": scores.get("pleasant"),
                    "readable": scores.get("readable"),
                    "native_vi": scores.get("native_vi"),
                },
                "flags": _flags(item),
            }
        )
    return "Hãy chấm các từ sau và trả JSON đúng schema:\n" + json.dumps(
        rows,
        ensure_ascii=False,
        indent=2,
    )


def call_openai(
    api_key: str,
    base_url: str,
    model: str,
    batch: List[Mapping[str, object]],
) -> List[Dict[str, object]]:
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": build_user_prompt(batch)}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "vietnamese_word_labels",
                "strict": True,
                "schema": LABEL_SCHEMA,
            }
        },
        "max_output_tokens": 5000,
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    data = response.json()
    output_text = data.get("output_text")
    if not output_text:
        chunks: List[str] = []
        for output in data.get("output", []):
            for content in output.get("content", []):
                text = content.get("text")
                if text:
                    chunks.append(text)
        output_text = "".join(chunks)
    if not output_text:
        raise RuntimeError(f"No output text in response: {json.dumps(data)[:1000]}")

    parsed = json.loads(output_text)
    labels = parsed.get("labels")
    if not isinstance(labels, list):
        raise RuntimeError(f"Invalid labels payload: {output_text[:1000]}")
    return [dict(label) for label in labels]


def _extract_json_object(text: str) -> Dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])

    raise RuntimeError(f"Could not parse JSON from model output: {text[:1000]}")


def call_ollama(
    ollama_url: str,
    model: str,
    batch: List[Mapping[str, object]],
) -> List[Dict[str, object]]:
    prompt = (
        SYSTEM_PROMPT
        + "\nChỉ trả về JSON hợp lệ, không markdown, theo dạng: "
        + '{"labels":[{"title":"...","pos":"...","label_keep":true,'
        + '"label_pleasant":4,"label_readable":5,"label_native_vi":4,'
        + '"label_note":"..."}]}\n\n'
        + build_user_prompt(batch)
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192,
        },
    }
    response = requests.post(
        f"{ollama_url.rstrip('/')}/api/generate",
        json=payload,
        timeout=180,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

    data = response.json()
    output_text = data.get("response", "")
    parsed = _extract_json_object(output_text)
    labels = parsed.get("labels")
    if not isinstance(labels, list):
        raise RuntimeError(f"Invalid Ollama labels payload: {output_text[:1000]}")
    return [dict(label) for label in labels]


def write_csv(path: Path, labels: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "title",
                "pos",
                "label_keep",
                "label_pleasant",
                "label_readable",
                "label_native_vi",
                "label_note",
            ],
        )
        writer.writeheader()
        for label in labels:
            writer.writerow(
                {
                    "title": label.get("title", ""),
                    "pos": label.get("pos", ""),
                    "label_keep": int(bool(label.get("label_keep"))),
                    "label_pleasant": label.get("label_pleasant", ""),
                    "label_readable": label.get("label_readable", ""),
                    "label_native_vi": label.get("label_native_vi", ""),
                    "label_note": label.get("label_note", ""),
                }
            )


def main() -> None:
    args = parse_args()
    items = select_items(
        Path(args.input),
        limit=args.limit,
        min_score=args.min_score,
        include_rejected=args.include_rejected,
    )
    cache_path = Path(args.cache)
    cached = load_cache(cache_path)
    labels: Dict[tuple[str, str], Dict[str, object]] = dict(cached)

    remaining = [
        item
        for item in items
        if (str(item.get("title", "")), str(item.get("pos", ""))) not in labels
    ]

    if args.dry_run:
        print(build_user_prompt(remaining[: args.batch_size] or items[: args.batch_size]))
        return

    api_key = os.getenv(args.api_key_env)
    if args.provider == "openai" and not api_key:
        raise SystemExit(f"Missing API key env var: {args.api_key_env}")

    for start in range(0, len(remaining), args.batch_size):
        batch = remaining[start : start + args.batch_size]
        if args.provider == "ollama":
            batch_labels = call_ollama(
                ollama_url=args.ollama_url,
                model=args.model,
                batch=batch,
            )
        else:
            batch_labels = call_openai(
                api_key=api_key or "",
                base_url=args.base_url,
                model=args.model,
                batch=batch,
            )
        append_cache(cache_path, batch_labels)
        for label in batch_labels:
            key = (str(label.get("title", "")), str(label.get("pos", "")))
            labels[key] = label
        print(
            f"labeled {min(start + args.batch_size, len(remaining))}/{len(remaining)}",
            flush=True,
        )
        if args.sleep:
            time.sleep(args.sleep)

    ordered_labels = [
        labels[(str(item.get("title", "")), str(item.get("pos", "")))]
        for item in items
        if (str(item.get("title", "")), str(item.get("pos", ""))) in labels
    ]
    write_csv(Path(args.output), ordered_labels)


if __name__ == "__main__":
    main()
