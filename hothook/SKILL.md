---
name: hothook
description: Analyze and deconstruct videos from YouTube, Douyin, Bilibili, or supplied video files, subtitles, transcripts, scripts, screenshots, or page evidence. Use when the user asks for a viral video teardown, hook analysis, verbatim transcript, script structure, pacing, title/thumbnail review, platform fit, virality reasons, rewrite directions, reusable creator templates, or a complete HTML/DOCX report. Default output is Chinese. For linked videos, prefer full-watch evidence collection; for verbatim scripts, require transcript/subtitle/ASR evidence.
---

# HotHook

## Core Rule

Break videos into evidence-based creator insights and reusable scripts. Default to Chinese unless the user requests another language.

Never claim a full video teardown from only a page snapshot, metadata, chapter summary, or single screenshot. Never call a frame-based reconstruction a verbatim transcript. If transcript, subtitles, or ASR output are unavailable, label the output as "脚本复原" instead of "逐字稿".

## Evidence Levels

Classify evidence before analysis:

1. **Transcript evidence**: official captions, subtitles, user-provided transcript/script, or ASR output. Required for "逐字稿".
2. **Full-watch evidence**: whole-timeline screenshots, sampled frames, or a local video file. Use for complete visual teardown and script-structure analysis.
3. **Page evidence**: title, metrics, description, comments, platform AI summary, chapters, and screenshots. Use for partial breakdown only.
4. **Link-only evidence**: URL without accessible content. Ask for transcript, subtitles, video file, screenshots, or permission to run browser collection.

## Full-Report Workflow

For linked videos in a Codex/browser-capable environment:

1. Read `references/browser_automation.md`.
2. Collect page evidence with `scripts/browser_collect_video_context.py`.
3. Verify the correct target video is loaded by checking title, author, duration, URL, and screenshot.
4. Prefer direct video URLs over unstable modal URLs when possible.
   - Douyin: `https://www.douyin.com/jingxuan?modal_id=<id>` -> `https://www.douyin.com/video/<id>`.
5. If the user asks for "逐字稿", obtain transcript evidence:
   - Use provided transcript/subtitle/script first.
   - Use platform captions/transcript when visible.
   - Use ASR for local video/audio when available.
   - Normalize transcript/subtitles with `scripts/normalize_transcript.py`.
   - If transcript evidence cannot be obtained, ask for it or downgrade to "脚本复原".
6. Collect full-watch visual evidence with `scripts/hothook_watch_video_timeline.py`.
7. Inspect frames from the beginning, middle, and end. If frames show a login wall, modal, homepage, wrong video, or blocked content, do not claim full-watch evidence.
8. Create contact sheets with `scripts/make_contact_sheets.py`.
9. Write the analysis and produce a final `.html` or `.docx` when requested. For one-file HTML, use `scripts/generate_single_html_report.py` to embed images.

## Required Output Modules

Every full breakdown must include:

1. **数据面板**: platform, URL, author, title, publish time, duration, visible metrics, interaction-rate decision, and data judgment.
2. **Hook 拆解**: first 3-15 seconds, hook type, stop-scroll mechanism, risk points, and rewrite advice.
3. **逐字稿 or 脚本复原**:
   - Use "逐字稿" only when transcript/subtitle/ASR evidence exists.
   - Use timestamped speaker text from beginning to end.
   - Do not invent missing lines.
   - If only full-watch frames exist, write "基于完整时间线截图和可见字幕复原，不是音频 ASR 逐字稿".
4. **脚本结构**: segment name, timestamp, content summary, narrative function, pacing, and reusable pattern.
5. **风格标签**: format, content category, emotional tone, editing/visual style, persona/account feel.
6. **为什么能爆**: 2-3 concrete reasons, each tied to mechanism, video evidence, and reusable lesson.
7. **改写方向**: 3 actionable directions with platform, account type, new hook, outline, title/cover suggestion, and pitfalls.

## Browser Rules

- Do not ask for or store passwords, cookies, session tokens, or 2FA codes.
- Use a persistent browser profile when login may be needed.
- If login, QR code, CAPTCHA, or 2FA appears, ask the user to complete it manually. Do not bypass platform security.
- Collect only visible page/video evidence relevant to the user request.
- Respect platform terms and rate limits; do not scrape at scale.

## Commands

Collect page evidence:

```bash
python scripts/browser_collect_video_context.py "<video-url>" --out hothook_evidence --profile .hothook-browser-profile --channel chrome --wait 20
```

Collect full timeline screenshots:

```bash
python scripts/hothook_watch_video_timeline.py "<video-url>" --out hothook_full_watch --profile .hothook-browser-profile --channel chrome --interval 5 --max-duration 600
```

Normalize transcript/subtitles:

```bash
python scripts/normalize_transcript.py "<transcript-or-subtitle-file>" --out hothook_transcript
```

Create contact sheets:

```bash
python scripts/make_contact_sheets.py --frames hothook_full_watch/frames --out hothook_full_watch/contact_sheets --sheet-span 60
```

Generate one-file HTML from a Markdown report:

```bash
python scripts/generate_single_html_report.py --markdown report.md --out final_report.html --title "HotHook 完整拆解报告" --embed hothook_full_watch/contact_sheets
```

## Quality Bar

- Separate confirmed evidence from inference.
- Tie every claim to visible metrics, transcript lines, frame evidence, scene choices, comments, or platform conventions.
- Do not provide long verbatim copyrighted transcripts beyond what the user provided or what is legally/technically appropriate to process for analysis.
- Final reports must state evidence status: transcript-backed, full-watch frame-backed, page-evidence-only, or partial.
