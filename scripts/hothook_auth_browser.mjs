#!/usr/bin/env node
import http from "node:http";
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";

function loadPlaywright() {
  try {
    return createRequire(import.meta.url)("playwright");
  } catch {}
  return createRequire(path.join(process.cwd(), "package.json"))("playwright");
}

const { chromium } = loadPlaywright();

const args = process.argv.slice(2);

function argValue(name, fallback = "") {
  const index = args.indexOf(name);
  if (index >= 0 && args[index + 1]) return args[index + 1];
  const prefix = `${name}=`;
  const pair = args.find((arg) => arg.startsWith(prefix));
  return pair ? pair.slice(prefix.length) : fallback;
}

function hasFlag(name) {
  return args.includes(name);
}

const profileDir = argValue(
  "--profile",
  process.env.HOTHOOK_PROFILE || path.join(os.homedir(), ".codex", "hothook-browser-profile"),
);
const browserChoice = argValue("--browser", "auto");
const port = Number(argValue("--port", "0"));
const keepOpen = hasFlag("--keep-open");

const siteUrls = {
  youtube: "https://www.youtube.com/",
  douyin: "https://www.douyin.com/",
  bilibili: "https://www.bilibili.com/",
};

const browserCandidates = [
  process.env.HOTHOOK_BROWSER,
  process.env.CHROME_PATH,
  browserChoice === "chrome" ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" : "",
  browserChoice === "msedge" ? "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe" : "",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);

async function findBrowser() {
  if (browserChoice === "chromium") return null;
  for (const candidate of browserCandidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {}
  }
  return null;
}

function pageHtml() {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HotHook 浏览器授权</title>
  <style>
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif; background:#f3f5f8; color:#15171a; }
    main { max-width:820px; margin:0 auto; padding:42px 22px; }
    section { background:#fff; border:1px solid #d9dee7; border-radius:8px; padding:26px; }
    h1 { margin:0 0 12px; font-size:26px; }
    p { color:#555d68; line-height:1.7; }
    .buttons { display:flex; flex-wrap:wrap; gap:12px; margin:22px 0; }
    button { border:1px solid #c9d0dc; background:#fff; padding:12px 16px; border-radius:6px; font-size:15px; cursor:pointer; }
    button.primary { background:#15171a; color:#fff; border-color:#15171a; }
    code { background:#eef1f5; padding:2px 5px; border-radius:4px; }
    #status { min-height:28px; font-weight:600; color:#137333; }
  </style>
</head>
<body>
  <main>
    <section>
      <h1>HotHook 浏览器授权</h1>
      <p>这个窗口使用 HotHook 固定浏览器资料夹。你只需要在下面平台登录一次，后续拆解视频会复用这个登录状态。</p>
      <p>资料夹：<code>${profileDir.replaceAll("&", "&amp;").replaceAll("<", "&lt;")}</code></p>
      <div class="buttons">
        <button onclick="openSite('youtube')">打开 YouTube 授权</button>
        <button onclick="openSite('douyin')">打开抖音授权</button>
        <button onclick="openSite('bilibili')">打开 B站授权</button>
        <button class="primary" onclick="done()">完成授权</button>
      </div>
      <p id="status"></p>
      <p>不要在聊天里发送密码、验证码、Cookie 或登录令牌。登录、扫码、2FA 都只在浏览器窗口里完成。</p>
    </section>
  </main>
  <script>
    async function openSite(site) {
      const response = await fetch('/open?site=' + encodeURIComponent(site));
      document.getElementById('status').textContent = await response.text();
    }
    async function done() {
      const response = await fetch('/done', { method: 'POST' });
      document.getElementById('status').textContent = await response.text();
    }
  </script>
</body>
</html>`;
}

const executablePath = await findBrowser();
const launchOptions = {
  headless: false,
  viewport: { width: 1280, height: 900 },
  locale: "zh-CN",
};
if (executablePath) {
  launchOptions.executablePath = executablePath;
} else if (browserChoice === "chrome" || browserChoice === "msedge") {
  launchOptions.channel = browserChoice;
}

await fs.mkdir(profileDir, { recursive: true });
const context = await chromium.launchPersistentContext(profileDir, launchOptions);

let finish;
const finished = new Promise((resolve) => {
  finish = resolve;
});

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url || "/", "http://127.0.0.1");
  if (url.pathname === "/") {
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(pageHtml());
    return;
  }
  if (url.pathname === "/open") {
    const site = url.searchParams.get("site") || "";
    const target = siteUrls[site];
    if (!target) {
      response.writeHead(400, { "content-type": "text/plain; charset=utf-8" });
      response.end("未知平台");
      return;
    }
    const page = await context.newPage();
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
    response.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    response.end(`已打开 ${site}，请在新标签页完成登录或授权。`);
    return;
  }
  if (url.pathname === "/done") {
    response.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    response.end(keepOpen ? "已记录。你可以手动关闭窗口。" : "授权完成，窗口即将关闭。");
    finish();
    return;
  }
  response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
  response.end("Not found");
});

await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
const address = server.address();
const authUrl = `http://127.0.0.1:${address.port}/`;
const page = await context.newPage();
await page.goto(authUrl);

console.log(`HotHook authorization page: ${authUrl}`);
console.log(`Profile: ${profileDir}`);
console.log("Finish login in the opened browser, then click 完成授权.");

process.on("SIGINT", () => finish());
process.on("SIGTERM", () => finish());

await finished;
server.close();
if (!keepOpen) {
  await context.close();
}
