// Run from repository root. Resets the shared LIVE demo and leaves it RESOLVED.
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const url = process.env.DEMO_URL || 'https://datasentinel-seven.vercel.app';
const output = resolve('docs/screenshots');
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
  headless: true,
});
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const page = await context.newPage();
page.setDefaultTimeout(120_000);
const captures = [];

async function click(name, endpoint) {
  const response = page.waitForResponse(r => r.url().endsWith(endpoint) && r.request().method() === 'POST');
  const refreshed = page.waitForResponse(r => r.url().endsWith('/api/state') && r.request().method() === 'GET');
  await page.getByRole('button', { name, exact: true }).click();
  const result = await response;
  if (!result.ok()) throw new Error(`${name} returned HTTP ${result.status()}`);
  await refreshed;
  await page.getByText(`${name} in progress…`, { exact: true }).waitFor({ state: 'hidden' });
  for (const alert of await page.getByRole('alert').all()) {
    const message = (await alert.innerText()).trim();
    if (message && await alert.isVisible()) throw new Error(message);
  }
}

async function capture(file, heading) {
  if (heading) {
    await page.getByRole('heading', { name: heading, exact: true }).evaluate(element => {
      element.scrollIntoView({ block: 'start' });
      window.scrollBy(0, -80);
    });
  } else await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: resolve(output, file), animations: 'disabled' });
  captures.push({ file, focus: heading || 'Status hero' });
}

try {
  await page.goto(url);
  await page.getByText('API connected', { exact: true }).waitFor();
  if (!(await page.locator('main > header').innerText()).includes('heuristic')) {
    throw new Error('Screenshot capture requires a heuristic backend; keep LLM_PROVIDER=heuristic.');
  }
  await click('Reset Demo', '/api/demo/reset');
  await click('Run Healthy Pipeline', '/api/pipeline/run');
  await page.getByText('HEALTHY', { exact: true }).first().waitFor();
  await page.getByText('110,000', { exact: true }).first().waitFor();
  await capture('healthy.png');
  await page.getByRole('combobox', { name: 'Incident type' }).selectOption('filter_regression');
  await click('Inject Incident', '/api/incidents/inject');
  await click('Run Pipeline', '/api/pipeline/run');
  await click('Detect', '/api/incidents/detect');
  await page.getByText('CRITICAL', { exact: true }).first().waitFor();
  await page.getByText('43,760', { exact: true }).first().waitFor();
  await capture('critical.png');
  await click('Investigate', '/api/incidents/INC-0001/investigate');
  await page.locator('pre').filter({ hasText: '| Final status | **ROOT_CAUSE_IDENTIFIED** |' }).waitFor();
  await capture('root-cause.png', 'Root cause');
  await capture('git-evidence.png', 'Offending change (git show)');
  await click('Generate Fix', '/api/incidents/INC-0001/fix');
  await page.locator('pre').filter({ hasText: '| Final status | **FIX_PROPOSED** |' }).waitFor();
  if (!(await page.getByRole('button', { name: 'Apply Fix', exact: true }).isEnabled())) throw new Error('Approval action unavailable');
  await capture('proposed-fix.png', 'Suggested remediation');
  await click('Apply Fix', '/api/incidents/INC-0001/apply');
  await click('Validate', '/api/incidents/INC-0001/validate');
  await page.getByText(/^INCIDENT INC-0001 RESOLVED/).first().waitFor();
  await page.locator('pre').filter({ hasText: '| Final status | **RESOLVED** |' }).waitFor();
  await capture('resolved.png');
  await capture('validation-passed.png', 'Validation');
  await writeFile(resolve(output, 'capture.json'), JSON.stringify({
    captured_at: new Date().toISOString(), viewport: { width: 1440, height: 1000 },
    source: url, provider: 'heuristic', rollback_fixture: false,
    unavailable_live_stages: ['validation-failed', 'rollback'],
    note: 'Correct hosted remediation passes validation; no failure was injected or mocked.',
    captures,
  }, null, 2) + '\n');
  console.log(`Captured ${captures.length} real dashboard images in ${output}`);
} finally { await browser.close(); }
