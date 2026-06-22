# Browser automation mode for Codex

Use this reference when the user wants HotHook to run inside Codex or another coding agent that can execute browser automation.

## Goal

Open the supplied YouTube, Douyin, or Bilibili URL in a real browser session, use the user's authenticated account when available, play the target video from start to end, collect visible page/video evidence plus transcript evidence, then produce the standard HotHook breakdown as a single HTML file.

## Safety and account rules

- Never ask the user to paste passwords, cookies, session tokens, or 2FA codes into chat.
- Prefer the global persistent browser profile so the user can log in manually once and reuse the authenticated session. The default profile is `%USERPROFILE%\.codex\hothook-browser-profile`, or `HOTHOOK_PROFILE` when set.
- If a login wall, CAPTCHA, 2FA, QR login, or security challenge appears, run `scripts/hothook_auth_browser.mjs` and ask the user to complete login in the opened HotHook browser. Do not try to bypass it.
- HotHook cannot attach to an arbitrary already-open normal browser window. Existing-browser reuse requires either the shared HotHook profile or a user-launched browser with remote debugging enabled.
- If ads, cookie prompts, or "continue watching" overlays interrupt playback, click only the normal visible controls provided by the page, such as "Skip Ad/跳过广告" or "Continue watching/继续播放", and record the action in the playback manifest.
- Respect platform terms and rate limits. Do not scrape at scale, evade bot detection, or access private content without the user's authorization.
- Treat personal/private creator dashboards and messages as sensitive. Only collect the current video page data needed for the requested breakdown.

## Recommended Codex workflow

1. Check whether the environment supports a browser.
   - Prefer the local built-in browser through Playwright (`--browser auto`), using installed Chrome or Edge before downloaded Chromium.
   - Use headed mode when login may be required.
2. Launch Chromium with the shared persistent profile directory, preferably the script default. Avoid project-local profile directories because they cause repeated logins.
3. Open the video URL.
4. If login is required, open the authorization button page with `node scripts/hothook_auth_browser.mjs`, ask the user to click the needed platform button, and complete login manually. After login, rerun the same collection command using the same profile.
5. After login, reload the page and collect:
   - URL and platform.
   - Page title, video title, creator name, publication time when visible.
   - Visible metrics: views, likes, comments, shares, favorites/coins/danmaku where available.
   - Description/caption text and visible hashtags.
   - Top visible comments when relevant and authorized.
   - Screenshot of the title/cover/player area and timestamped frames while the video plays.
   - Available subtitles/transcript/captions from the page UI when visible.
6. Save raw evidence to a local folder such as `hothook_evidence/`:
   - `page_snapshot.json`
   - `page_text.txt`
   - `screenshot.png`
   - optional `transcript.txt`
7. Play the video from start to end with `scripts/hothook_watch_video_timeline.py --browser auto --require-complete`. Do not use random seeking as proof of full watch.
   - While playback runs, allow normal visible clicks for skip-ad and resume controls; these are evidence-handling actions, not security or ad bypass.
8. Run the standard HotHook breakdown using the collected evidence and write a single HTML report.

## Full-playback workflow

Use this when the user asks for a complete script, complete teardown, or final HTML/DOCX report from a linked video.

1. First collect page evidence with `scripts/browser_collect_video_context.py`.
2. Confirm the page is the target video by checking author, title, duration, and at least one screenshot.
3. Prefer direct video URLs over modal URLs when modal URLs are unstable.
   - Douyin modal example: `https://www.douyin.com/jingxuan?modal_id=<id>`
   - Douyin direct example: `https://www.douyin.com/video/<id>`
4. Obtain transcript evidence before final analysis: platform captions, supplied subtitles/transcript, or ASR output from a local video/audio file.
5. Normalize transcript or subtitle files with `scripts/normalize_transcript.py`.
6. Collect full-playback visual evidence with `scripts/hothook_watch_video_timeline.py --browser auto --require-complete`.
7. Inspect frames from the beginning, middle, and end before analysis, and verify the manifest says `completed: true`.
8. Reject a full-playback claim if frames show a login wall, homepage/feed, wrong video, cookie/security prompt, or static blocked screen.
9. If transcript/audio evidence is unavailable, do not invent a verbatim transcript. Produce a blocked/partial HTML that states what is missing and asks for subtitles, transcript, audio, or a local video file.
10. For final delivery, create a single HTML file. Embed images in the HTML as data URIs. Use `scripts/generate_single_html_report.py` for single-file HTML when a Markdown report and evidence images are available.

## Evidence hierarchy

Prefer evidence in this order:
1. User-provided video file, subtitles, transcript, or script.
2. Browser-collected complete playback manifest, visible captions/transcript, page text, metrics, comments, and screenshots.
3. User-provided screenshots or notes.
4. Link-only metadata.

Do not infer exact dialogue, visual cuts, or retention behavior from a link alone. If browser collection gets only metrics and no transcript, do not produce a complete teardown. Produce a single HTML that clearly marks the job as blocked/partial.

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

Then create a partial HTML report instead of chat-only output, clearly stating that complete teardown requires full-playback and transcript evidence.
