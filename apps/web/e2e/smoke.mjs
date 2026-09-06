/**
 * Browser smoke test.
 *
 * playwright-core rather than playwright, so it drives the Chrome that is
 * already installed instead of downloading a browser. In CI, CHROME_PATH
 * points at the runner's Chrome.
 *
 * The test that matters is the last one. The weighting switch is the whole
 * argument of the project, and if flipping it stopped changing the numbers
 * the product would have no point. That is worth a real browser rather than
 * a unit test on a reducer.
 */
import { chromium } from "playwright-core";

const BASE = process.env.WEB_BASE_URL ?? "http://127.0.0.1:3000";
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const CHROME =
  process.env.CHROME_PATH ??
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

let passed = 0;
const failures = [];

async function check(name, fn) {
  try {
    await fn();
    console.log(`  pass  ${name}`);
    passed += 1;
  } catch (error) {
    console.log(`  FAIL  ${name}`);
    console.log(`        ${error.message}`);
    failures.push(name);
  }
}

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

try {
  const variants = await (await fetch(`${API}/variants?limit=100`)).json();
  const scored = variants.filter((v) => !v.is_suppressed);
  assert(scored.length > 0, "no scored variants; run the pipeline first");
  const variant = scored[0];

  await check("home page renders the headline", async () => {
    await page.goto(BASE, { waitUntil: "networkidle" });
    const h1 = await page.textContent("h1");
    assert(h1.includes("Not every review"), `unexpected headline: ${h1}`);
  });

  await check("the wordmark uses the embedded font", async () => {
    const family = await page.$eval(".brand-mark", (el) =>
      getComputedStyle(el).fontFamily,
    );
    assert(family.includes("Revix Wordmark"), `wordmark font is ${family}`);
  });

  // Scoped to the dropdown, not to the page. A bare a[href^="/v/"] also
  // matches the vehicle links in the page body, so the test passed even when
  // the type-ahead was returning nothing at all.
  await check("search finds a vehicle as you type", async () => {
    await page.fill('input[type="search"]', variant.model.slice(0, 5));
    const results = "[data-search-results]";
    try {
      await page.waitForSelector(`${results} a[href^="/v/"]`, { timeout: 5000 });
    } catch {
      // The dropdown always renders something, so quoting it says why. A
      // blocked cross-origin fetch reads "Search is unavailable", which the
      // API answers with a healthy 200 and would otherwise look fine.
      const said = (await page.textContent(results).catch(() => "")).trim();
      throw new Error(`the type-ahead returned no vehicle; it said: "${said.slice(0, 120)}"`);
    }
    const count = await page.$$eval(`${results} a[href^="/v/"]`, (els) => els.length);
    assert(count > 0, "type-ahead returned nothing");
  });

  await check("browse lists the catalogue", async () => {
    await page.goto(`${BASE}/browse`, { waitUntil: "networkidle" });
    const rows = await page.$$eval("table tbody tr", (els) => els.length);
    assert(rows > 5, `only ${rows} rows in the catalogue`);
  });

  await check("the verdict page renders a score and its range", async () => {
    await page.goto(`${BASE}/v/${variant.id}`, { waitUntil: "networkidle" });
    const score = await page.textContent(".score-anim");
    assert(/^\d+\.\d$/.test(score.trim()), `score reads "${score}"`);
    const body = await page.textContent("body");
    assert(body.includes("confident range"), "no confidence range shown");
    assert(body.includes("effective sample"), "no effective sample shown");
  });

  await check("topics are ordered by disagreement, not by score", async () => {
    const scores = await page.$$eval(".score-anim", (els) =>
      els.slice(1).map((e) => parseFloat(e.textContent)),
    );
    const sortedDesc = [...scores].sort((a, b) => b - a);
    assert(
      JSON.stringify(scores) !== JSON.stringify(sortedDesc) || scores.length < 3,
      "topics look sorted by score, which is the thing we do not do",
    );
  });

  await check("THE FLAGSHIP: flipping the switch changes the numbers", async () => {
    const before = await page.$$eval(".score-anim", (els) =>
      els.map((e) => e.textContent.trim()),
    );
    await page.click('.seg button:has-text("equally")');
    await page.waitForTimeout(600);
    const after = await page.$$eval(".score-anim", (els) =>
      els.map((e) => e.textContent.trim()),
    );
    assert(
      JSON.stringify(before) !== JSON.stringify(after),
      "the switch changed nothing, which would make the whole product pointless",
    );
    const body = await page.textContent("body");
    assert(body.includes("This is the baseline"), "baseline copy did not appear");
  });

  await check("clicking through to the evidence works", async () => {
    await page.goto(`${BASE}/v/${variant.id}`, { waitUntil: "networkidle" });
    const link = await page.$('a[href^="/evidence/"]');
    assert(link, "no evidence link on the verdict page");
    await link.click();
    await page.waitForURL("**/evidence/**", { timeout: 8000 });
    // waitForURL resolves when navigation commits, which is before the server
    // component has streamed in. Wait for actual content, not just the URL.
    await page.waitForSelector("text=Counted for", { timeout: 8000 });
    const body = await page.textContent("body");
    assert(body.includes("Counted for"), "evidence weights are not shown");
    assert(body.includes("The reviews behind"), "evidence heading missing");
  });

  await check("compare suggests two different vehicles, not one twice", async () => {
    // Variants arrive ordered by model, so pairing adjacent entries produced
    // "Activa vs Activa": twelve trims of one scooter, compared with itself.
    await page.goto(`${BASE}/compare`, { waitUntil: "load" });
    const labels = await page.$$eval('a[href^="/compare?a="]', (els) =>
      els.map((e) => e.textContent.trim()),
    );
    assert(labels.length > 0, "no suggested pairs at all");
    const selfPairs = labels.filter((l) => {
      const [left, right] = l.split(" vs ").map((s) => s.trim());
      return left && right && left === right;
    });
    assert(
      selfPairs.length === 0,
      `a vehicle is being compared with itself: ${selfPairs.join(", ")}`,
    );
  });

  await check("every top-level page answers", async () => {
    for (const path of ["/method", "/accuracy", "/sources", "/status", "/compare"]) {
      const response = await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" });
      assert(response.status() === 200, `${path} returned ${response.status()}`);
    }
  });
} finally {
  await browser.close();
}

console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
