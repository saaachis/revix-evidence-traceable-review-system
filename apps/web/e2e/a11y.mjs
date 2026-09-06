/**
 * Accessibility audit with axe-core, driven through the same browser the
 * smoke test uses.
 *
 * Runs the WCAG 2.1 AA rule set over every top-level page. Automated checks
 * catch perhaps a third of real accessibility problems, so a clean run here
 * is a floor rather than a certificate.
 */
import { chromium } from "playwright-core";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const AXE = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

const BASE = process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000";
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const CHROME =
  process.env.CHROME_PATH ?? "C:/Program Files/Google/Chrome/Application/chrome.exe";

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

const variants = await (await fetch(`${API}/variants?limit=100`)).json();
const scored = variants.find((v) => !v.is_suppressed) ?? variants[0];

const routes = [
  ["home", "/"],
  ["browse", "/browse"],
  ["search", "/search?q=creta"],
  ["compare", "/compare"],
  ["method", "/method"],
  ["accuracy", "/accuracy"],
  ["sources", "/sources"],
  ["status", "/status"],
  ["verdict", `/v/${scored.id}`],
];

let total = 0;
const seen = new Map();

for (const [name, path] of routes) {
  await page.goto(`${BASE}${path}`, { waitUntil: "load" });
  await page.waitForTimeout(400);
  await page.evaluate(AXE);
  const result = await page.evaluate(async () =>
    // @ts-expect-error injected
    await window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    }),
  );
  const violations = result.violations;
  total += violations.length;
  console.log(`  ${violations.length === 0 ? "pass" : "FAIL"}  ${name.padEnd(9)} ${violations.length} issue types`);
  for (const v of violations) {
    seen.set(v.id, v);
    console.log(`          ${v.impact.padEnd(8)} ${v.id}: ${v.help} (${v.nodes.length} nodes)`);
    console.log(`            e.g. ${v.nodes[0].target.join(" ")}`);
  }
}

await browser.close();
console.log(`\n${seen.size} distinct issue types across ${routes.length} pages`);
process.exit(total === 0 ? 0 : 1);
