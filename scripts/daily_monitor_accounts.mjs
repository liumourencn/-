#!/usr/bin/env node
/**
 * Monitor YouTube/Douyin accounts and de-duplicate HotHook breakdown jobs.
 *
 * scan:
 *   node scripts/daily_monitor_accounts.mjs --config config/watch_accounts.json --mode scan
 *
 * mark after a report is generated:
 *   node scripts/daily_monitor_accounts.mjs --config config/watch_accounts.json --mode mark --url "<video-url>" --report "<html-path>" --status completed
 */

import fs from "node:fs/promises";
import fssync from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const WINDOWS_BROWSER_PATHS = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

function parseArgs(argv) {
  const args = {
    mode: "scan",
    config: "config/watch_accounts.json",
    url: "",
    report: "",
    status: "completed",
  };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2).replaceAll("-", "_");
    const next = argv[index + 1];
    if (next && !next.startsWith("--")) {
      args[key] = next;
      index += 1;
    } else {
      args[key] = true;
    }
  }
  return args;
}

function nowIso() {
  return new Date().toISOString();
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await fs.readFile(file, "utf8"));
  } catch {
    return fallback;
  }
}

async function writeJson(file, data) {
  await fs.mkdir(path.dirname(path.resolve(file)), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function resolveFromConfig(configPath, value) {
  if (!value) return value;
  if (path.isAbsolute(value)) return value;
  return path.resolve(path.dirname(path.resolve(configPath)), value);
}

function normalizeVideo(inputUrl, platformHint = "") {
  let url = String(inputUrl || "").trim();
  if (!url) return null;
  if (url.startsWith("//")) url = `https:${url}`;
  if (url.startsWith("/")) {
    if (platformHint === "douyin") url = `https://www.douyin.com${url}`;
    if (platformHint === "youtube") url = `https://www.youtube.com${url}`;
  }

  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  const host = parsed.hostname.replace(/^www\./, "");
  const platform = platformHint || (host.includes("douyin") ? "douyin" : host.includes("youtube") || host.includes("youtu.be") ? "youtube" : "");
  let id = "";
  let canonicalUrl = parsed.toString();

  if (platform === "youtube") {
    if (parsed.searchParams.get("v")) id = parsed.searchParams.get("v");
    const shorts = parsed.pathname.match(/\/shorts\/([A-Za-z0-9_-]{8,})/);
    if (!id && shorts) id = shorts[1];
    if (!id && host === "youtu.be") id = parsed.pathname.split("/").filter(Boolean)[0] || "";
    if (id) canonicalUrl = `https://www.youtube.com/watch?v=${id}`;
  }

  if (platform === "douyin") {
    const video = parsed.pathname.match(/\/video\/(\d+)/);
    if (video) id = video[1];
    if (!id && parsed.searchParams.get("modal_id")) id = parsed.searchParams.get("modal_id");
    if (id) canonicalUrl = `https://www.douyin.com/video/${id}`;
  }

  if (!platform || !id) return null;
  return {
    key: `${platform}:${id}`,
    id,
    platform,
    url: canonicalUrl,
  };
}

function findBuiltinBrowser() {
  const candidates = [process.env.HOTHOOK_BROWSER, process.env.CHROME_PATH, ...WINDOWS_BROWSER_PATHS].filter(Boolean);
  for (const candidate of candidates) {
    if (fssync.existsSync(candidate)) return candidate;
  }
  return null;
}

async function launchContext(config, configPath) {
  let chromium;
  try {
    const requireFromCwd = createRequire(path.join(process.cwd(), "hothook-monitor-runtime.js"));
    chromium = requireFromCwd("playwright").chromium;
  } catch (error) {
    throw new Error(`Playwright is required for scan mode. Run npm install playwright in the working folder. ${error}`);
  }
  const executablePath = config.browser === "auto" || !config.browser ? findBuiltinBrowser() : null;
  const profile = resolveFromConfig(configPath, config.profile || ".hothook-browser-profile");
  const options = {
    headless: Boolean(config.headless),
    viewport: { width: 1440, height: 1000 },
    locale: "zh-CN",
  };
  if (executablePath) options.executablePath = executablePath;
  if (config.browser === "chrome") options.channel = "chrome";
  if (config.browser === "msedge") options.channel = "msedge";
  return chromium.launchPersistentContext(profile, options);
}

async function closePrompts(page) {
  for (const label of ["我知道了", "知道了", "稍后再说", "取消", "Accept all", "Reject all", "I agree"]) {
    try {
      await page.getByText(label, { exact: true }).click({ timeout: 1200 });
      await page.waitForTimeout(500);
      return;
    } catch {}
  }
  try {
    await page.keyboard.press("Escape");
  } catch {}
}

async function extractVideosFromPage(page, account) {
  await page.goto(account.url, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(account.wait_ms || 6000);
  await closePrompts(page);
  await page.waitForTimeout(1500);

  const links = await page.evaluate(() => {
    const anchors = [...document.querySelectorAll("a[href]")];
    return anchors.map((anchor) => ({
      href: anchor.href || anchor.getAttribute("href") || "",
      text: anchor.innerText || anchor.getAttribute("aria-label") || anchor.title || "",
    }));
  });

  const candidates = [];
  for (const link of links) {
    const normalized = normalizeVideo(link.href, account.platform);
    if (normalized) {
      candidates.push({
        ...normalized,
        account_name: account.name || account.url,
        account_url: account.url,
        title_hint: link.text.trim(),
        discovered_at: nowIso(),
      });
    }
  }

  const seen = new Set();
  return candidates.filter((candidate) => {
    if (seen.has(candidate.key)) return false;
    seen.add(candidate.key);
    return true;
  }).slice(0, account.max_videos || 12);
}

function videoWasProcessed(record) {
  if (!record) return false;
  if (record.status !== "completed") return false;
  if (!record.report_path) return true;
  return fssync.existsSync(record.report_path);
}

async function scan(configPath) {
  const config = await readJson(configPath, null);
  if (!config) throw new Error(`Config not found or invalid: ${configPath}`);
  const statePath = resolveFromConfig(configPath, config.state_path || "hothook_monitor_state/seen_videos.json");
  const outputPath = resolveFromConfig(configPath, config.output_path || "hothook_monitor_state/pending_videos.json");
  const state = await readJson(statePath, { version: 1, videos: {} });

  const context = await launchContext(config, configPath);
  const page = await context.newPage();
  const pending = [];
  const skipped = [];
  const errors = [];

  for (const account of config.accounts || []) {
    try {
      const videos = await extractVideosFromPage(page, account);
      for (const video of videos) {
        const record = state.videos[video.key];
        if (videoWasProcessed(record)) {
          skipped.push({ ...video, reason: "already_deconstructed", report_path: record.report_path || "" });
          continue;
        }
        if (!record) {
          state.videos[video.key] = {
            ...video,
            first_seen_at: nowIso(),
            status: "pending",
            report_path: "",
          };
        }
        pending.push({ ...video, previous_status: state.videos[video.key].status || "pending" });
      }
    } catch (error) {
      errors.push({ account: account.name || account.url, error: String(error) });
    }
  }

  state.updated_at = nowIso();
  await writeJson(statePath, state);
  const result = {
    generated_at: nowIso(),
    pending,
    skipped,
    errors,
    state_path: statePath,
  };
  await writeJson(outputPath, result);
  await context.close();
  console.log(JSON.stringify(result, null, 2));
}

async function mark(configPath, args) {
  const config = await readJson(configPath, {});
  const statePath = resolveFromConfig(configPath, config.state_path || "hothook_monitor_state/seen_videos.json");
  const state = await readJson(statePath, { version: 1, videos: {} });
  const normalized = normalizeVideo(args.url);
  if (!normalized) throw new Error(`Cannot normalize video URL: ${args.url}`);
  const oldRecord = state.videos[normalized.key] || {};
  state.videos[normalized.key] = {
    ...oldRecord,
    ...normalized,
    status: args.status || "completed",
    report_path: args.report ? path.resolve(args.report) : oldRecord.report_path || "",
    processed_at: nowIso(),
    updated_at: nowIso(),
  };
  state.updated_at = nowIso();
  await writeJson(statePath, state);
  console.log(JSON.stringify(state.videos[normalized.key], null, 2));
}

const args = parseArgs(process.argv.slice(2));
if (args.mode === "scan") {
  await scan(args.config);
} else if (args.mode === "mark") {
  await mark(args.config, args);
} else {
  throw new Error(`Unknown mode: ${args.mode}`);
}
