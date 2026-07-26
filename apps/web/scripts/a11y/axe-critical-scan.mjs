import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

const baseUrl = process.env.A11Y_BASE_URL || "http://127.0.0.1:4173";
const reportPath = process.env.A11Y_REPORT_PATH || "./a11y-report.json";
const defaultRoutes = ["/", "/home", "/login", "/discover/accounts"];
const routes = (process.env.A11Y_ROUTES || "")
  .split(",")
  .map((route) => route.trim())
  .filter(Boolean);
if (routes.length === 0) {
  routes.push(...defaultRoutes);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

const routeResults = [];

for (const route of routes) {
  const url = `${baseUrl}${route}`;
  await page.goto(url, { waitUntil: "networkidle" });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();

  routeResults.push({
    route,
    url,
    violations: results.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      nodes: violation.nodes.length,
      selectors: violation.nodes.flatMap((node) => node.target),
    })),
  });
}

await browser.close();

const summary = routeResults.reduce(
  (acc, item) => {
    for (const violation of item.violations) {
      if (violation.impact === "critical") acc.critical += 1;
      if (violation.impact === "serious") acc.serious += 1;
      acc.total += 1;
    }
    return acc;
  },
  { critical: 0, serious: 0, total: 0 },
);

const payload = {
  generatedAt: new Date().toISOString(),
  standard: "WCAG 2.1 AA",
  routes,
  summary,
  results: routeResults,
};

await fs.mkdir(path.dirname(reportPath), { recursive: true });
await fs.writeFile(reportPath, JSON.stringify(payload, null, 2));
console.log(`Accessibility report written to ${reportPath}`);
console.log(`Summary: ${summary.total} total, ${summary.serious} serious, ${summary.critical} critical violations`);
