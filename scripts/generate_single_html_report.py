#!/usr/bin/env python3
"""Generate a portable single-file HTML report from Markdown and image folders."""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import pathlib
import re


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a single-file HotHook HTML report")
    parser.add_argument("--markdown", required=True, help="Markdown report written by the agent")
    parser.add_argument("--out", required=True, help="Output HTML file")
    parser.add_argument("--title", default="HotHook 完整拆解报告")
    parser.add_argument("--embed", action="append", default=[], help="Image file or directory to embed; can be repeated")
    return parser.parse_args()


def markdown_to_html(markdown: str) -> str:
    blocks: list[str] = []
    in_table = False
    table_rows: list[str] = []

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not in_table:
            return
        rows = [row for row in table_rows if not re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", row)]
        html_rows = []
        for index, row in enumerate(rows):
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            tag = "th" if index == 0 else "td"
            html_rows.append("<tr>" + "".join(f"<{tag}>{html.escape(cell)}</{tag}>" for cell in cells) + "</tr>")
        blocks.append("<table>" + "".join(html_rows) + "</table>")
        in_table = False
        table_rows = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if "|" in line and line.strip().startswith("|"):
            in_table = True
            table_rows.append(line)
            continue
        flush_table()

        if not line.strip():
            continue
        if line.startswith("# "):
            blocks.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            blocks.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            blocks.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            blocks.append(f"<p class='bullet'>• {html.escape(line[2:].strip())}</p>")
        elif line.startswith("> "):
            blocks.append(f"<blockquote>{html.escape(line[2:].strip())}</blockquote>")
        else:
            safe = html.escape(line)
            safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
            blocks.append(f"<p>{safe}</p>")
    flush_table()
    return "\n".join(blocks)


def iter_images(paths: list[str]) -> list[pathlib.Path]:
    images: list[pathlib.Path] = []
    for value in paths:
        path = pathlib.Path(value)
        if path.is_dir():
            images.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}))
        elif path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            images.append(path)
    return images


def image_data_uri(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def main() -> int:
    args = parse_args()
    markdown_path = pathlib.Path(args.markdown)
    out_path = pathlib.Path(args.out)
    body = markdown_to_html(markdown_path.read_text(encoding="utf-8-sig"))

    evidence_html = []
    for image in iter_images(args.embed):
        evidence_html.append(
            f"<figure><img src='{image_data_uri(image)}' alt='{html.escape(image.name)}'><figcaption>{html.escape(str(image))}</figcaption></figure>"
        )

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(args.title)}</title>
  <style>
    body {{ margin:0; background:#f6f2ea; color:#111318; font-family:"Microsoft YaHei","PingFang SC",sans-serif; line-height:1.7; }}
    main {{ width:min(1120px, calc(100% - 40px)); margin:0 auto; padding:42px 0 70px; }}
    section, article {{ background:#fff; border:1px solid #d9dde4; box-shadow:0 16px 38px rgba(17,19,24,.1); padding:28px; margin:0 0 22px; }}
    h1 {{ font-size:42px; line-height:1.12; margin:0 0 20px; }}
    h2 {{ margin-top:28px; border-left:8px solid #cf3d31; padding-left:12px; }}
    h3 {{ color:#235f73; margin-top:22px; }}
    table {{ width:100%; border-collapse:collapse; margin:14px 0; }}
    th, td {{ border:1px solid #d9dde4; padding:10px 12px; text-align:left; vertical-align:top; }}
    th {{ background:#eef1f5; }}
    blockquote {{ margin:12px 0; padding:12px 14px; background:#111318; color:#f2f5f8; }}
    .bullet {{ margin:6px 0; }}
    figure {{ margin:18px 0; }}
    img {{ max-width:100%; height:auto; border:1px solid #d9dde4; display:block; }}
    figcaption {{ color:#606a75; font-size:12px; margin-top:6px; word-break:break-all; }}
  </style>
</head>
<body>
  <main>
    <article>{body}</article>
    <section>
      <h2>证据图片</h2>
      {''.join(evidence_html) if evidence_html else '<p>未嵌入图片。</p>'}
    </section>
  </main>
</body>
</html>
"""
    out_path.write_text(document, encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
