#!/usr/bin/env python3
"""Collect visible video-page evidence for HotHook using Playwright.

This script is intended for Codex-like environments. It opens a supplied URL in a
persistent Chromium profile so the user can log in manually if needed. It does
not bypass login, CAPTCHA, 2FA, paywalls, or platform restrictions.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone


WINDOWS_BROWSER_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def default_profile_dir() -> str:
    """Return the stable profile reused across HotHook runs."""
    return os.environ.get(
        "HOTHOOK_PROFILE",
        str(pathlib.Path.home() / ".codex" / "hothook-browser-profile"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect HotHook browser evidence")
    parser.add_argument("url", help="YouTube, Douyin, Bilibili, or similar video URL")
    parser.add_argument("--out", default="hothook_evidence", help="Output directory")
    parser.add_argument("--profile", default=default_profile_dir(), help="Persistent browser profile directory")
    parser.add_argument("--headless", action="store_true", help="Run browser headless; not recommended for login")
    parser.add_argument("--wait", type=int, default=20, help="Seconds to wait after page load")
    parser.add_argument("--browser", default="auto", choices=("auto", "chromium", "chrome", "msedge"), help="Browser to use; auto prefers the local built-in browser")
    parser.add_argument("--channel", default=None, help="Optional Playwright channel override, such as chrome or msedge")
    return parser.parse_args()


def builtin_browser_executable() -> str | None:
    env_path = os.environ.get("HOTHOOK_BROWSER") or os.environ.get("CHROME_PATH")
    candidates = [env_path] if env_path else []
    candidates.extend(WINDOWS_BROWSER_PATHS)
    for candidate in candidates:
        if candidate and pathlib.Path(candidate).exists():
            return candidate
    return None


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_metric(value: str) -> int | str:
    normalized = value.strip().replace(",", "")
    if normalized.endswith("万"):
        try:
            return int(float(normalized[:-1]) * 10000)
        except ValueError:
            return value
    try:
        return int(normalized)
    except ValueError:
        return value


def extract_visible_video_data(snapshot: dict[str, object], body_text: str) -> dict[str, object]:
    lines = _clean_lines(body_text)
    data: dict[str, object] = {
        "platform": "Douyin" if "douyin.com" in str(snapshot.get("url", "")) else "unknown",
        "url": snapshot.get("url"),
        "requested_url": snapshot.get("requested_url"),
        "collected_at": snapshot.get("collected_at"),
        "page_title": snapshot.get("title"),
        "visible_metrics": {},
        "chapters": [],
        "hashtags": [],
        "raw_extraction_note": "Heuristic extraction from visible page text; verify against screenshot when precision matters.",
    }

    time_line_index = next((i for i, line in enumerate(lines) if re.fullmatch(r"\d{2}:\d{2}\s*/\s*\d{2}:\d{2}", line)), None)
    if time_line_index is not None:
        current_position, duration = [part.strip() for part in lines[time_line_index].split("/", 1)]
        data["current_position"] = current_position
        data["duration"] = duration

    author_index = next((i for i, line in enumerate(lines) if line.startswith("@")), None)
    if author_index is not None:
        data["author"] = lines[author_index]
        if author_index + 1 < len(lines) and lines[author_index + 1].startswith("·"):
            data["published"] = lines[author_index + 1].lstrip("·").strip()
        if author_index + 2 < len(lines):
            data["video_title"] = lines[author_index + 2]
        if author_index + 3 < len(lines):
            description = lines[author_index + 3]
            data["description"] = description
            data["hashtags"] = re.findall(r"#([^#\s]+)", description)

    try:
        loop_index = lines.index("连播")
        metric_values: list[str] = []
        for line in lines[loop_index + 1 :]:
            if line == "听抖音":
                break
            if re.fullmatch(r"\d+(?:\.\d+)?万?", line):
                metric_values.append(line)
        metric_names = ("likes", "comments", "favorites", "shares")
        data["visible_metrics"] = {
            name: _parse_metric(value)
            for name, value in zip(metric_names, metric_values)
        }
    except ValueError:
        pass

    if "章节要点" in lines:
        chapter_start = lines.index("章节要点")
        summary_lines: list[str] = []
        chapters: list[dict[str, object]] = []
        current_chapter: dict[str, object] | None = None
        for line in lines[chapter_start + 1 :]:
            if re.fullmatch(r"\d{2}:\d{2}\s*/\s*\d{2}:\d{2}", line):
                break
            if re.fullmatch(r"\d{2}:\d{2}", line):
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = {"time": line}
                continue
            if current_chapter is not None and "title" not in current_chapter:
                current_chapter["title"] = line
                continue
            if current_chapter is None:
                summary_lines.append(line)
            elif line and not line.startswith("・"):
                current_chapter.setdefault("details", [])
                details = current_chapter["details"]
                if isinstance(details, list):
                    details.append(line)
        if current_chapter:
            chapters.append(current_chapter)
        data["ai_summary_visible_on_page"] = "\n".join(summary_lines).strip()
        data["chapters"] = chapters

    return data


def launch_context(playwright, args: argparse.Namespace):
    launch_options = {
        "user_data_dir": args.profile,
        "headless": args.headless,
        "viewport": {"width": 1440, "height": 1000},
        "locale": "zh-CN",
    }
    if args.channel:
        launch_options["channel"] = args.channel
    elif args.browser == "chrome":
        launch_options["channel"] = "chrome"
    elif args.browser == "msedge":
        launch_options["channel"] = "msedge"
    elif args.browser == "auto":
        executable = builtin_browser_executable()
        if executable:
            launch_options["executable_path"] = executable

    try:
        return playwright.chromium.launch_persistent_context(**launch_options)
    except Exception:
        if args.browser != "auto":
            raise
        launch_options.pop("executable_path", None)
        for channel in ("chrome", "msedge"):
            launch_options["channel"] = channel
            try:
                return playwright.chromium.launch_persistent_context(**launch_options)
            except Exception:
                continue
        launch_options.pop("channel", None)
        return playwright.chromium.launch_persistent_context(**launch_options)


def extract_transcript(page) -> list[str]:
    patterns = (
        r"Show transcript",
        r"Transcript",
        r"显示文字记录",
        r"显示转录",
        r"文字记录",
    )
    try:
        page.get_by_text(re.compile(r"more|更多|展开", re.IGNORECASE)).first.click(timeout=2500)
        time.sleep(1)
    except Exception:
        pass

    for pattern in patterns:
        try:
            page.get_by_text(re.compile(pattern, re.IGNORECASE)).first.click(timeout=3000)
            time.sleep(2)
            lines = page.locator("ytd-transcript-segment-renderer").all_inner_texts()
            cleaned = [line.strip() for line in lines if line.strip()]
            if cleaned:
                return cleaned
        except Exception:
            pass
    return []


def main() -> int:
    args = parse_args()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception as exc:  # pragma: no cover - depends on runtime
        print("Playwright is not installed. Install with: pip install playwright && playwright install chromium", file=sys.stderr)
        print(f"Import error: {exc}", file=sys.stderr)
        return 2

    with sync_playwright() as p:
        context = launch_context(p, args)
        page = context.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            pass

        print("Browser opened. If login is required, complete it in the browser window.")
        for label in ("我知道了", "知道了", "稍后再说", "取消"):
            try:
                page.get_by_text(label, exact=True).click(timeout=3000)
                print(f"Closed visible prompt: {label}")
                break
            except Exception:
                pass
        print(f"Waiting {args.wait} seconds before collecting visible evidence...")
        time.sleep(args.wait)

        try:
            title = page.title()
        except Exception:
            title = ""
        try:
            body_text = page.locator("body").inner_text(timeout=10000)
        except Exception:
            body_text = ""
        try:
            html_lang = page.locator("html").get_attribute("lang", timeout=5000)
        except Exception:
            html_lang = None

        snapshot = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "url": page.url,
            "requested_url": args.url,
            "title": title,
            "html_lang": html_lang,
            "note": "Visible page evidence only. Login/CAPTCHA/2FA bypass was not attempted.",
        }
        transcript_lines = extract_transcript(page)
        snapshot["transcript_line_count"] = len(transcript_lines)
        snapshot["transcript_evidence"] = bool(transcript_lines)

        (out_dir / "page_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "page_text.txt").write_text(body_text, encoding="utf-8")
        (out_dir / "transcript.txt").write_text("\n".join(transcript_lines), encoding="utf-8")
        video_data = extract_visible_video_data(snapshot, body_text)
        (out_dir / "video_data.json").write_text(json.dumps(video_data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            page.screenshot(path=str(out_dir / "screenshot.png"), full_page=True)
        except Exception as exc:
            (out_dir / "screenshot_error.txt").write_text(str(exc), encoding="utf-8")

        context.close()

    print(f"Saved HotHook evidence to: {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
