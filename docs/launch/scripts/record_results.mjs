// Record an editorial close-up of results from the verified YouTube query.
import { chromium } from "playwright";
import { mkdtemp, readFile, writeFile, copyFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const assets = join(project, "assets/browser");
const run = JSON.parse(
  await readFile(join(assets, "youtube-actions.json"), "utf8"),
);
if (!run.outcome?.ok)
  throw new Error("First record a successful Nudge search.");
const query = run.actions.find((a) => a.operation === "type").text;
const directory = await mkdtemp(join(tmpdir(), "nudge-results-"));
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 1,
  recordVideo: { dir: directory, size: { width: 1280, height: 800 } },
});
const page = await context.newPage();
await page.goto(
  "https://www.youtube.com/results?search_query=" + encodeURIComponent(query),
  { waitUntil: "domcontentloaded" },
);
const candidates = page
  .locator("ytd-video-renderer")
  .filter({
    has: page
      .locator("a#video-title")
      .filter({ hasText: /how.*change.*tire/i }),
  });
await candidates.first().waitFor({ state: "attached", timeout: 20000 });
const titles = await candidates.locator("a#video-title").allTextContents();
const target = candidates.first();
await target.evaluate((e) => e.scrollIntoView({ block: "start" }));
await page.mouse.wheel(0, -115);
await page.waitForTimeout(2500);
await page.screenshot({ path: join(assets, "youtube-results-closeup.png") });
await writeFile(
  join(assets, "youtube-results-closeup.json"),
  JSON.stringify(
    {
      query,
      title: titles[0]?.trim(),
      purpose:
        "Editorial result close-up after the verified Nudge search. Browser scrolling for this shot is manual.",
    },
    null,
    2,
  ) + "\n",
);
await page.waitForTimeout(2200);
await context.close();
await copyFile(
  await page.video().path(),
  join(assets, "youtube-result-closeup.webm"),
);
await browser.close();
console.log(JSON.stringify({ query, title: titles[0]?.trim() }));
