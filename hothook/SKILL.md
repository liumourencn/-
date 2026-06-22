---
name: hothook
description: Analyze and deconstruct videos from YouTube, Douyin, Bilibili, or supplied video files, subtitles, transcripts, scripts, screenshots, or page evidence. Use when the user asks for a viral video teardown, hook analysis, verbatim transcript, script structure, pacing, title/thumbnail review, platform fit, virality reasons, rewrite directions, reusable creator templates, daily account monitoring, new-video detection, duplicate breakdown prevention, or a complete report. Default output is Chinese and the final deliverable must be a single HTML file. For linked videos, require full-playback evidence and transcript/subtitle/ASR evidence before claiming a complete breakdown or verbatim transcript.
---

# HotHook

## Core Rule

Break videos into evidence-based creator insights and reusable scripts. Default to Chinese unless the user requests another language. The final deliverable is always a single `.html` file unless the user explicitly asks for an additional format.

Never claim a full video teardown from only a page snapshot, metadata, chapter summary, or single screenshot. Never call a frame-based reconstruction a verbatim transcript. If transcript, subtitles, or ASR output are unavailable, stop before final analysis and ask the user for subtitles/transcript/audio/video, or explain that only a partial page-evidence HTML can be produced.

## Evidence Levels

Classify evidence before analysis:

1. **Transcript evidence**: official captions, subtitles, user-provided transcript/script, or ASR output. Required for "逐字稿".
2. **Full-playback evidence**: the video was played from start to end in a browser or local player, with a manifest proving start time, end time, duration, sampled screenshots, and completion status. Required for a complete linked-video teardown.
3. **Page evidence**: title, metrics, description, comments, platform AI summary, chapters, and screenshots. Use for partial breakdown only.
4. **Link-only evidence**: URL without accessible content. Ask for transcript, subtitles, video file, screenshots, or permission to run browser collection.

## Full-Report Workflow

For linked videos in a Codex/browser-capable environment:

1. Read `references/browser_automation.md`.
2. Collect page evidence with `scripts/browser_collect_video_context.py`.
3. Verify the correct target video is loaded by checking title, author, duration, URL, and screenshot.
4. Prefer direct video URLs over unstable modal URLs when possible.
   - Douyin: `https://www.douyin.com/jingxuan?modal_id=<id>` -> `https://www.douyin.com/video/<id>`.
5. Obtain transcript evidence before final analysis:
   - Use provided transcript/subtitle/script first.
   - Use platform captions/transcript when visible.
   - Use ASR for local video/audio when available.
   - Normalize transcript/subtitles with `scripts/normalize_transcript.py`.
   - If transcript evidence cannot be obtained, create a blocked/partial HTML that states what is missing and asks for transcript/subtitles/audio/video.
6. Collect full-playback visual evidence with `scripts/hothook_watch_video_timeline.py --require-complete`.
7. Inspect frames from the beginning, middle, and end, and verify `full_playback_manifest.json` has `completed: true`. If frames show a login wall, modal, homepage, wrong video, blocked content, or repeated static screen, do not claim full-playback evidence.
8. Create contact sheets with `scripts/make_contact_sheets.py`.
9. Write the analysis as Markdown, then always produce a final single-file `.html` with `scripts/generate_single_html_report.py`, embedding evidence images/contact sheets. Return the HTML path as the primary output.

## Daily Account Monitoring

Use this workflow when the user wants HotHook to monitor specified Douyin or YouTube accounts every day:

1. Create a config from `config/watch_accounts.example.json`.
2. Run `scripts/daily_monitor_accounts.mjs --mode scan` before any breakdown work.
3. Read `pending_videos.json`.
4. For every pending video:
   - If it is already marked `completed` in `seen_videos.json` and the report path still exists, skip it.
   - If it is `pending`, `failed`, or has no completed report path, run the full-report workflow.
5. After a report is successfully generated, run `scripts/daily_monitor_accounts.mjs --mode mark --url "<video-url>" --report "<html-path>" --status completed`.
6. If breakdown fails, mark it as `failed` only when useful for audit. Do not mark failed videos as completed.

The state file is the source of truth for duplicate prevention. Do not rely only on filenames or dates.

## Required Output Modules

Every full breakdown must include:

1. **数据面板**: platform, URL, author, title, publish time, duration, visible metrics, interaction-rate decision, and data judgment.
2. **Hook 拆解**: first 3-15 seconds, hook type, stop-scroll mechanism, risk points, and rewrite advice.
3. **逐字稿**:
   - Use "逐字稿" only when transcript/subtitle/ASR evidence exists.
   - Use timestamped speaker text from beginning to end.
   - Do not invent missing lines.
   - If transcript evidence is missing, do not fabricate this module. Produce an HTML that states the missing evidence and asks for transcript/subtitle/audio/video, or run ASR if a local media file is available.
4. **脚本结构**: segment name, timestamp, content summary, narrative function, pacing, and reusable pattern.
5. **风格标签**: format, content category, emotional tone, editing/visual style, persona/account feel.
6. **为什么能爆**: 2-3 concrete reasons, each tied to mechanism, video evidence, and reusable lesson.
7. **改写方向**: 3 actionable directions with platform, account type, new hook, outline, title/cover suggestion, and pitfalls.

## Browser Rules

- Do not ask for or store passwords, cookies, session tokens, or 2FA codes.
- Use the local built-in browser by default (`--browser auto`), preferring installed Chrome or Edge before Playwright's downloaded Chromium.
- Reuse the same global persistent browser profile for every run. The default script profile is `%USERPROFILE%\.codex\hothook-browser-profile`, overridable with `HOTHOOK_PROFILE`.
- If the platform asks for login, run `scripts/hothook_auth_browser.mjs` and ask the user to click the platform authorization button in the opened HotHook browser. After login, rerun collection with the same profile instead of creating a project-local profile.
- Do not use a project-local guest profile for YouTube/Douyin/Bilibili unless the user explicitly asks for a fresh session.
- Do not claim that HotHook can attach to any already-open normal browser window. Existing-browser reuse is only possible when the user intentionally starts Chrome/Edge with a remote debugging port, or when using the HotHook shared profile.
- If login, QR code, CAPTCHA, or 2FA appears, ask the user to complete it manually. Do not bypass platform security.
- During full playback, click only normal visible playback controls when they interrupt collection, such as YouTube "Skip Ad/跳过广告", "Continue watching/继续播放", cookie prompts, or a visible play button. Record these actions in `full_playback_manifest.json`. Do not block ads, alter network requests, hide sponsorships, or use ad-bypass extensions.
- Collect only visible page/video evidence relevant to the user request.
- Respect platform terms and rate limits; do not scrape at scale.

## Commands

Open the HotHook authorization page with platform login buttons:

```bash
node scripts/hothook_auth_browser.mjs
```

Optional: keep the authorized browser window open after clicking "完成授权":

```bash
node scripts/hothook_auth_browser.mjs --keep-open
```

Collect page evidence:

```bash
python scripts/browser_collect_video_context.py "<video-url>" --out hothook_evidence --browser auto --wait 20
```

Collect full-playback evidence:

```bash
python scripts/hothook_watch_video_timeline.py "<video-url>" --out hothook_full_watch --browser auto --interval 5 --require-complete
```

Legacy one-time login warmup when YouTube/Douyin/Bilibili asks for account verification:

```bash
python scripts/browser_collect_video_context.py "https://www.youtube.com/" --out hothook_login_check --browser auto --wait 90
```

After the user finishes login in the opened browser, rerun the target video command. Do not switch `--profile` unless the user intentionally wants a fresh login session.

Normalize transcript/subtitles:

```bash
python scripts/normalize_transcript.py "<transcript-or-subtitle-file>" --out hothook_transcript
```

Create contact sheets:

```bash
python scripts/make_contact_sheets.py --frames hothook_full_watch/frames --out hothook_full_watch/contact_sheets --sheet-span 60
```

Generate the required one-file HTML from a Markdown report:

```bash
python scripts/generate_single_html_report.py --markdown report.md --out final_report.html --title "HotHook 完整拆解报告" --embed hothook_full_watch/contact_sheets
```

Scan monitored accounts and skip videos already deconstructed:

```bash
node scripts/daily_monitor_accounts.mjs --config config/watch_accounts.json --mode scan
```

Mark a video as deconstructed after HTML generation:

```bash
node scripts/daily_monitor_accounts.mjs --config config/watch_accounts.json --mode mark --url "<video-url>" --report "<html-path>" --status completed
```

## Quality Bar

- Separate confirmed evidence from inference.
- Tie every claim to visible metrics, transcript lines, frame evidence, scene choices, comments, or platform conventions.
- Do not provide long verbatim copyrighted transcripts beyond what the user provided or what is legally/technically appropriate to process for analysis.
- Final reports must state evidence status: transcript-backed, full-playback-backed, page-evidence-only, or blocked by missing transcript/full-playback evidence.
- Do not finish a linked-video request with chat-only analysis when the user asked to use this skill. Create and return an HTML file.
