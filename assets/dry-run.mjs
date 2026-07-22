import { chromium } from "playwright";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const deck = path.join(__dirname, "..", "index.html");
const out = path.join(__dirname, "screenshots", "_dry-run-slide.png");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
page.on("pageerror", (err) => errors.push(String(err)));
page.on("response", (res) => {
  if (res.status() >= 400) errors.push(`${res.status()} ${res.url()}`);
});

await page.goto("file:///" + deck.replace(/\\/g, "/"), { waitUntil: "networkidle" });
const slideCount = await page.locator(".slide").count();
const active = await page.locator(".slide.active").count();
await page.locator(".slide.active").screenshot({ path: out });

// Advance through all slides; ensure each has active class and no broken imgs
for (let i = 0; i < slideCount; i++) {
  await page.keyboard.press("ArrowRight");
}
await page.keyboard.press("Home");
const broken = await page.evaluate(() => {
  return Array.from(document.images)
    .filter((img) => !img.complete || img.naturalWidth === 0)
    .map((img) => img.src);
});

console.log(JSON.stringify({ slideCount, active, broken, errors }, null, 2));
await browser.close();
