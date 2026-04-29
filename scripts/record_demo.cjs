const { chromium } = require("playwright");
const fs = require("node:fs/promises");
const path = require("node:path");

const baseUrl = process.env.LEARNGUARD_DEMO_URL || "http://127.0.0.1:8788";
const outputDir = path.resolve("output/videos");
const longPauseMs = Number(process.env.LEARNGUARD_DEMO_LONG_PAUSE_MS || 7000);
const mediumPauseMs = Number(process.env.LEARNGUARD_DEMO_MEDIUM_PAUSE_MS || 4500);
const shortPauseMs = Number(process.env.LEARNGUARD_DEMO_SHORT_PAUSE_MS || 2500);

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  await fs.mkdir(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    recordVideo: {
      dir: outputDir,
      size: { width: 1440, height: 1100 },
    },
  });
  const page = await context.newPage();

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await wait(mediumPauseMs);

  await page.getByRole("button", { name: "Start Session" }).click();
  await wait(mediumPauseMs);

  await page.getByRole("button", { name: "Use Partial Answer" }).click();
  await page.waitForFunction(() =>
    document.body.innerText.includes("Gate blocked Codex action"),
  );
  await page.locator("#blockedAction").scrollIntoViewIfNeeded();
  await wait(longPauseMs);
  await page.locator("#gatePanelTitle").scrollIntoViewIfNeeded();
  await wait(longPauseMs);

  await page.getByRole("button", { name: "Start Session" }).click();
  await wait(mediumPauseMs);

  await page.getByRole("button", { name: "Use Full Concept Answer" }).click();
  await page.waitForFunction(() =>
    document.body.innerText.includes("Level 4 - Workspace Unlock"),
  );
  await page.waitForFunction(() => document.body.innerText.includes("4 passed"));
  await wait(mediumPauseMs);

  await page.locator("#diffOutput").scrollIntoViewIfNeeded();
  await wait(longPauseMs);
  await page.locator("#pytestOutput").scrollIntoViewIfNeeded();
  await wait(longPauseMs);

  const nextButton = page.getByRole("button", { name: "Next" }).first();
  await page.locator("#visualTraceCounter").scrollIntoViewIfNeeded();
  for (let index = 0; index < 3; index += 1) {
    await wait(shortPauseMs);
    if (await nextButton.isEnabled()) {
      await nextButton.click();
    }
  }
  await wait(mediumPauseMs);

  await page.locator("#evalSummary").scrollIntoViewIfNeeded();
  await wait(longPauseMs);
  await page.locator("#levelName").scrollIntoViewIfNeeded();
  await wait(mediumPauseMs);

  const video = page.video();
  await context.close();
  await browser.close();

  if (!video) {
    throw new Error("Playwright did not produce a video artifact.");
  }

  const rawPath = await video.path();
  const webmPath = path.join(outputDir, "learnguard_demo.webm");
  await fs.rm(webmPath, { force: true });
  await fs.copyFile(rawPath, webmPath);
  if (rawPath !== webmPath) {
    await fs.rm(rawPath, { force: true });
  }
  console.log(webmPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
