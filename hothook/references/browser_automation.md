# Browser automation mode for Codex

Use this reference when the user wants HotHook to run inside Codex or another coding agent that can execute browser automation.

## Goal

Open the supplied YouTube, Douyin, or Bilibili URL in a real browser session, use the user's authenticated account when available, collect only visible page/video evidence, then produce the standard HotHook breakdown.

## Safety and account rules

- Never ask the user to paste passwords, cookies, session tokens, or 2FA codes into chat.
- Prefer a persistent browser profile so the user can log in manually once and reuse the authenticated session.
- If a login wall, CAPTCHA, 2FA, QR login, or security challenge appears, pause and ask the user to complete it in the opened browser. Do not try to bypass it.
- Respect platform terms and rate limits. Do not scrape at scale, evade bot detection, or access private content without the user's authorization.
- Treat personal/private creator dashboards and messages as sensitive. Only collect the current video page data needed for the requested breakdown.

## Recommended Codex workflow

1. Check whether the environment supports a browser.
   - Prefer Playwright with Chromium.
   - Use headed mode when login may be required.
2. Launch Chromium with a persistent profile directory, for example `.hothook-browser-profile`.
3. Open the video URL.
4. If login is required, keep the browser open and ask the user to log in manually.
5. After login, reload the page and collect:
   - URL and platform.
   - Page title, video title, creator name, publication time when visible.
   - Visible metrics: views, likes, comments, shares, favorites/coins/danmaku where available.
   - Description/caption text and visible hashtags.
   - Top visible comments when relevant and authorized.
   - Screenshot of the title/cover/player area and a few representative frames if visible.
   - Available subtitles/transcript/captions from the page UI when visible.
6. Save raw evidence to a local folder such as `hothook_evidence/`:
   - `page_snapshot.json`
   - `page_text.txt`
   - `screenshot.png`
   - optional `transcript.txt`
7. Run the standard HotHook breakdown using the collected evidence.

## Full-watch workflow

Use this when the user asks for a complete script, complete teardown, or final HTML/DOCX report from a linked video.

1. First collect page evidence with `scripts/browser_collect_video_context.py`.
2. Confirm the page is the target video by checking author, title, duration, and at least one screenshot.
3. Prefer direct video URLs over modal URLs when modal URLs are unstable.
   - Douyin modal example: `https://www.douyin.com/jingxuan?modal_id=<id>`
   - Douyin direct example: `https://www.douyin.com/video/<id>`
4. If the user asks for 逐字稿, obtain transcript evidence first: platform captions, supplied subtitles/transcript, or ASR output from a local video/audio file.
5. Normalize transcript or subtitle files with `scripts/normalize_transcript.py`.
6. Collect full timeline visual evidence with `scripts/hothook_watch_video_timeline.py`.
7. Inspect frames from the beginning, middle, and end before analysis.
8. Reject a full-watch claim if frames show a login wall, homepage/feed, wrong video, cookie/security prompt, or static blocked screen.
9. If only frame evidence is available and no transcript/audio is available, call the script “基于完整时间线截图和可见字幕复原”, not a verbatim transcript.
10. For final delivery, create a single HTML or DOCX file. If the user wants one file, embed images in the HTML as data URIs or use DOCX embedded media. Use `scripts/generate_single_html_report.py` for single-file HTML when a Markdown report and evidence images are available.

## Evidence hierarchy

Prefer evidence in this order:
1. User-provided video file, subtitles, transcript, or script.
2. Browser-collected visible page text, metrics, captions, comments, and screenshots.
3. User-provided screenshots or notes.
4. Link-only metadata.

Do not infer exact dialogue, visual cuts, or retention behavior from a link alone. If browser collection gets only metrics and no transcript, still fill required modules but mark script-level details as limited.

## Platform notes

### YouTube

Useful page targets:
- Title, channel, view count, publish date, like count.
- Description and chapters.
- Transcript panel when available.
- Comments, only if useful for virality/comment-trigger analysis.

### Douyin

Useful page targets:
- Title/caption, creator, likes, comments, favorites, shares, publish time if visible.
- On-screen text from screenshots if readable.
- Comments and hashtags.

Douyin may require QR or app login. Pause for manual login instead of attempting credential automation.

### Bilibili

Useful page targets:
- Title, UP主, views, danmaku, comments, likes, coins, favorites, shares, publish time.
- Description, tags, chapters/sections when visible.
- Top comments and visible danmaku themes when useful.

## Browser failure fallback

If browser automation fails, report what failed briefly, then ask the user for one of:
- subtitle/transcript,
- copied title + caption/description + metrics,
- screenshots,
- uploaded video file.

Then continue with a partial breakdown rather than stopping completely.
