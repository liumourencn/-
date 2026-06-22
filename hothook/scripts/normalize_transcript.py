#!/usr/bin/env python3
"""Normalize TXT, SRT, or VTT transcripts into Markdown and JSON."""

from __future__ import annotations

import argparse
import json
import pathlib
import re


TIME_RE = re.compile(r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)\s*-->\s*(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize transcript/subtitle files")
    parser.add_argument("input", help="Input .txt, .srt, or .vtt file")
    parser.add_argument("--out", default="hothook_transcript", help="Output directory")
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_subtitle(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        time_index = next((i for i, line in enumerate(lines) if TIME_RE.search(line)), None)
        if time_index is None:
            continue
        match = TIME_RE.search(lines[time_index])
        if not match:
            continue
        content = clean_text(" ".join(lines[time_index + 1 :]))
        if content:
            entries.append({"start": match.group("start"), "end": match.group("end"), "text": content})
    return entries


def parse_plain_text(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in text.splitlines():
        line = clean_text(line)
        if line:
            entries.append({"start": "", "end": "", "text": line})
    return entries


def main() -> int:
    args = parse_args()
    input_path = pathlib.Path(args.input)
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8-sig")
    suffix = input_path.suffix.lower()
    entries = parse_subtitle(text) if suffix in {".srt", ".vtt"} else parse_plain_text(text)

    payload = {
        "source": str(input_path),
        "entry_count": len(entries),
        "evidence_type": "transcript",
        "entries": entries,
    }
    (out_dir / "transcript.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# HotHook 逐字稿", ""]
    for entry in entries:
        timestamp = entry["start"] if entry["start"] else "未标注"
        lines.append(f"- **{timestamp}** {entry['text']}")
    (out_dir / "transcript.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_dir / "transcript.json")
    print(out_dir / "transcript.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
