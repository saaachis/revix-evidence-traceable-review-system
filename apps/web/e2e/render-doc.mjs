/**
 * Render a paged HTML document to PDF, one sheet per `.page`.
 *
 * Lives here rather than in scripts/ because this is where playwright-core is
 * installed, next to the smoke test and the accessibility audit that use the
 * same browser.
 *
 * Headless Edge via --print-to-pdf was the obvious route and it silently
 * disagreed with the stylesheet: a thirteen-sheet document came out as
 * sixteen, with no page overflowing when measured. preferCSSPageSize makes
 * the @page rule authoritative instead of the printer's own defaults, which
 * is the whole reason this file exists.
 *
 *   node e2e/render-doc.mjs <input.html> <output.pdf>
 */
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: node e2e/render-doc.mjs <input.html> <output.pdf>");
  process.exit(1);
}

const CHROME =
  process.env.CHROME_PATH ??
  "C:/Users/Shinde/AppData/Local/ms-playwright/chromium-1187/chrome-win/chrome.exe";

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage();

await page.goto(pathToFileURL(resolve(input)).href, { waitUntil: "load" });
// Webfonts decide the height of every block on the sheet, so measuring or
// printing before they land produces a different document than the one on
// screen.
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(400);

await page.pdf({
  path: resolve(output),
  printBackground: true,
  preferCSSPageSize: true,
  margin: { top: "0", right: "0", bottom: "0", left: "0" },
});

const sheets = await page.evaluate(() => document.querySelectorAll(".page").length);
console.log(`${sheets} sheets rendered to ${output}`);

await browser.close();
