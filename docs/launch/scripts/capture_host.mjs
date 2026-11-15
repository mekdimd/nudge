import { chromium } from "playwright";
import { spawn } from "node:child_process";
import {
  mkdtemp,
  readFile,
  writeFile,
  copyFile,
  mkdir,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(project, "../..");
const [caseName, url, goal, envFile] = process.argv.slice(2);
if (!caseName || !url || !goal)
  throw new Error("Usage: capture_host.mjs CASE URL GOAL [ENV_FILE]");
const allowed =
  url.startsWith("http://127.0.0.1:8765/") ||
  url === "https://www.youtube.com/";
if (!allowed)
  throw new Error(
    "Record only the local sample pages or public YouTube search.",
  );
const rpc = await mkdtemp(join(tmpdir(), "nudge-capture-"));
const assets = join(project, "assets/browser");
await mkdir(assets, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 1,
  colorScheme: "light",
  recordVideo: { dir: rpc, size: { width: 1280, height: 800 } },
});
const recordingStarted = Date.now();
const page = await context.newPage();
const downloads = [];
page.on("download", async (download) => {
  const path = join(rpc, download.suggestedFilename());
  await download.saveAs(path);
  const bytes = await readFile(path);
  downloads.push({
    name: download.suggestedFilename(),
    bytes: bytes.length,
    pdf: bytes.subarray(0, 8).toString() === "%PDF-1.4",
  });
});
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(1500);
const actions = [];
const started = Date.now();
let last = 0,
  done = false;
await page.screenshot({ path: join(assets, caseName + "-page-idle.png") });
const child = spawn(
  "uv",
  [
    "run",
    "python",
    join(project, "scripts/capture_browser.py"),
    "--case",
    caseName,
    "--goal",
    goal,
    "--rpc",
    rpc,
    ...(envFile ? ["--env-file", envFile] : []),
  ],
  { cwd: root, stdio: ["ignore", "pipe", "pipe"] },
);
let log = "",
  stdoutLog = "";
child.stdout.on("data", (d) => {
  log += d;
  stdoutLog += d;
  process.stdout.write(d);
});
child.stderr.on("data", (d) => {
  log += d;
});
child.on("exit", () => (done = true));
try {
  while (!done) {
    let request;
    try {
      request = JSON.parse(await readFile(join(rpc, "request.json"), "utf8"));
    } catch {
      await page.waitForTimeout(20);
      continue;
    }
    if (request.id === last) {
      await page.waitForTimeout(20);
      continue;
    }
    last = request.id;
    let value = null,
      error = null;
    try {
      if (request.operation === "snapshot") {
        value = await page.evaluate(() => {
          let n = 0;
          const controls = [];
          const candidates = document.querySelectorAll(
            'button,a[href],input,textarea,select,[role="button"],[role="link"],[role="textbox"],[role="searchbox"],[role="combobox"]',
          );
          for (const el of candidates) {
            const b = el.getBoundingClientRect(),
              style = getComputedStyle(el);
            if (
              b.width <= 0 ||
              b.height <= 0 ||
              b.bottom < 0 ||
              b.right < 0 ||
              b.x > innerWidth ||
              b.y > innerHeight ||
              style.visibility === "hidden" ||
              style.display === "none"
            )
              continue;
            const tag = el.tagName.toLowerCase();
            let role =
              el.getAttribute("role") ||
              {
                a: "link",
                button: "button",
                input: "text field",
                textarea: "text area",
                select: "text field",
              }[tag];
            role =
              {
                textbox: "text field",
                searchbox: "search field",
                combobox: "text field",
              }[role] || role;
            if (
              tag === "input" &&
              ["checkbox", "radio", "hidden", "password"].includes(el.type)
            )
              continue;
            let label =
              el.getAttribute("aria-label") ||
              el.getAttribute("placeholder") ||
              el.innerText?.trim() ||
              el.getAttribute("title") ||
              "";
            const labelled = el.getAttribute("aria-labelledby");
            if (labelled)
              label = labelled
                .split(" ")
                .map((id) => document.getElementById(id)?.innerText || "")
                .join(" ");
            const id = "capture-" + ++n;
            el.dataset.nudgeRef = id;
            controls.push({
              id,
              label: label.slice(0, 200),
              role,
              enabled: !el.disabled,
              value: el.value ?? null,
              bounds: { x: b.x, y: b.y, w: b.width, h: b.height },
            });
          }
          const progress = document.querySelector(
            "yt-page-navigation-progress",
          );
          return {
            title: document.title,
            width: innerWidth,
            height: innerHeight,
            controls: controls.slice(0, 180),
            loading:
              document.readyState === "loading" ||
              Boolean(progress?.hasAttribute("active")),
          };
        });
        await page.screenshot({
          path: join(assets, caseName + "-state-" + actions.length + ".png"),
        });
      } else {
        const action = { ...request, at: (Date.now() - started) / 1000 };
        actions.push(action);
        console.log(
          JSON.stringify({
            case: caseName,
            operation: request.operation,
            label: request.label,
          }),
        );
        const locator = page.locator(
          '[data-nudge-ref="' + request.control_id + '"]',
        );
        if (request.operation === "click") {
          await locator.click({ clickCount: request.count || 1 });
          await page.waitForTimeout(500);
        } else if (request.operation === "type")
          await locator.fill(request.text);
        else if (request.operation === "type_focused")
          await page.keyboard.insertText(request.text);
        else if (request.operation === "navigate") {
          if (!request.url.startsWith("https://www.youtube.com/"))
            throw new Error("Recording navigation must stay on YouTube.");
          await page.goto(request.url, { waitUntil: "domcontentloaded" });
        } else if (request.operation === "scroll")
          await page.mouse.wheel(0, request.delta);
        else if (request.operation === "key")
          await page.keyboard.press(
            {
              enter: "Enter",
              escape: "Escape",
              tab: "Tab",
              back: "Alt+ArrowLeft",
            }[request.name] || request.name,
          );
        else
          throw new Error("Unknown recording operation " + request.operation);
      }
    } catch (e) {
      error = String(e);
    }
    await writeFile(
      join(rpc, "response.json"),
      JSON.stringify({ id: request.id, value, error }),
    );
  }
  await page.waitForTimeout(750);
  await page.screenshot({ path: join(assets, caseName + "-page-done.png") });
  const title = await page.title();
  const sent = await page.evaluate(() => window.sentMessage || null);
  if (child.exitCode !== 0)
    throw new Error(
      "The Qt recording process failed. Check the local capture log.",
    );
  const trace = JSON.parse(
    await readFile(join(assets, caseName + "-trace.json"), "utf8"),
  );
  await writeFile(
    join(assets, caseName + "-actions.json"),
    JSON.stringify(
      {
        case: caseName,
        epochStarted: started / 1000,
        recordingOffset: (started - recordingStarted) / 1000,
        actions,
        title,
        sent,
        downloads,
        outcome: trace.outcome,
      },
      null,
      2,
    ) + "\n",
  );
  if (!trace.outcome?.ok)
    throw new Error("Nudge did not finish: " + JSON.stringify(trace.outcome));
  if (
    caseName === "bank" &&
    (!title.includes("downloaded") ||
      !downloads.some((d) => d.name === "October-2026-statement.pdf" && d.pdf))
  )
    throw new Error("Statement PDF download did not complete.");
  if (caseName === "youtube" && !page.url().includes("/results?"))
    throw new Error("Search results did not load.");
  if (caseName === "mail" && (!sent || !trace.confirmed_before_action))
    throw new Error("Mail did not reach an approved local Send result.");
} finally {
  await context.close();
  await copyFile(await page.video().path(), join(assets, caseName + ".webm"));
  await browser.close();
  await writeFile(join(rpc, "capture.log"), log);
  await writeFile(join(assets, caseName + "-console.log"), stdoutLog);
  console.log("Recording log: " + join(rpc, "capture.log"));
}
