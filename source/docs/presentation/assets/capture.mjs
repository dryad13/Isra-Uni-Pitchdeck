import { chromium } from "playwright";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "screenshots");
const captureFile = path.join(__dirname, "capture-screens.html");
const addonFile = path.join(__dirname, "capture-addon.html");

const coreScreens = [
  ["s01", "01-shell-run-exam.png"],
  ["s02", "02-step-exam-session.png"],
  ["s03", "03-step-answer-key.png"],
  ["s04", "04-step-scanning.png"],
  ["s05", "05-results-queue.png"],
  ["s06", "06-batch-review.png"],
  ["s07", "07-sheet-detail.png"],
  ["s08", "08-reports-export.png"],
  ["s09", "09-roster.png"],
  ["s10", "10-tools-hub.png"],
  ["s11", "11-calibrator.png"],
  ["s12", "12-accuracy-lab.png"],
  ["s13", "13-isra-sheet-sample.png"],
];

const addonScreens = [
  ["s15", "15-addon-item-analysis.png"],
  ["s16", "16-addon-trends.png"],
  ["s17", "17-addon-export-report.png"],
];

async function capture(page, fileUrl, screens) {
  await page.goto(fileUrl, { waitUntil: "networkidle" });
  for (const [id, name] of screens) {
    const el = page.locator(`#${id}`);
    await el.scrollIntoViewIfNeeded();
    await el.screenshot({ path: path.join(outDir, name), type: "png" });
    console.log("captured", name);
  }
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await capture(page, "file:///" + captureFile.replace(/\\/g, "/"), coreScreens);
await capture(page, "file:///" + addonFile.replace(/\\/g, "/"), addonScreens);
await browser.close();
console.log("done");
