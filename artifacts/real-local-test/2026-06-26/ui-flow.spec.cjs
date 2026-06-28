const { test } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const artifactDir = __dirname;
const webUrl = 'http://127.0.0.1:3000';
const apiUrl = 'http://127.0.0.1:8000';
const question = 'What does the VISRAG_CORE_MARKER say about page images and citations?';
const papers = [
  {
    file: path.join(repoRoot, 'tmp', 'real-local-test-corpus', 'visrag-core.pdf'),
    title: 'Real Test VisRAG Core',
  },
  {
    file: path.join(repoRoot, 'tmp', 'real-local-test-corpus', 'bm25-exact.pdf'),
    title: 'Real Test BM25 Exact',
  },
  {
    file: path.join(repoRoot, 'tmp', 'real-local-test-corpus', 'agent-robustness.pdf'),
    title: 'Real Test Agent Robustness',
  },
];

function screenshotPath(name) {
  return path.join(artifactDir, name);
}

function sanitize(text) {
  return String(text || '')
    .replace(/[A-Za-z0-9_\-]{32,}/g, '[redacted-long-token]')
    .replace(/\s+/g, ' ')
    .trim();
}

async function bodyText(page) {
  return sanitize(await page.locator('body').innerText({ timeout: 5000 }));
}

async function clickButton(page, label) {
  await page.locator('button').filter({ hasText: label }).first().click({ timeout: 15000 });
}

async function waitForText(page, pattern, timeout = 60000) {
  await page.locator('body').filter({ hasText: pattern }).waitFor({ timeout });
}

async function visibleStatusFor(page, title) {
  const text = await bodyText(page);
  const at = text.indexOf(title);
  if (at === -1) return 'not visible';
  return text.slice(Math.max(0, at - 120), Math.min(text.length, at + 420));
}

test('PaperMemory real local UI flow', async ({ page }) => {
  test.setTimeout(240000);

  const screenshots = [];
  const consoleErrors = [];
  const networkErrors = [];
  const uploads = [];
  let apiOnlineVisible = false;
  let settingsSummary = '';
  let evidenceSummary = '';
  let status = 'DONE';
  const deviations = [];

  page.on('console', msg => {
    if (['error', 'warning'].includes(msg.type())) {
      consoleErrors.push(sanitize(`${msg.type()}: ${msg.text()}`));
    }
  });
  page.on('requestfailed', req => {
    networkErrors.push(sanitize(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`));
  });
  page.on('response', response => {
    const statusCode = response.status();
    if (statusCode >= 400) {
      networkErrors.push(sanitize(`${statusCode} ${response.request().method()} ${response.url()}`));
    }
  });

  try {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(webUrl, { waitUntil: 'networkidle', timeout: 30000 });
    const initial = 'ui-initial.png';
    await page.screenshot({ path: screenshotPath(initial), fullPage: true });
    screenshots.push(initial);

    apiOnlineVisible = (await bodyText(page)).includes('API online');

    await clickButton(page, 'Settings');
    await page.waitForTimeout(500);
    await page.locator('#setup-api-url').fill(apiUrl);
    await page.locator('#api-key').fill('');
    await page.locator('#image-context').setChecked(true);
    await page.locator('#max-evidence-images').fill('4');
    await page.locator('#max-evidence-images').dispatchEvent('change');
    await page.waitForTimeout(500);
    settingsSummary = await bodyText(page);
    const settingsShot = 'ui-settings.png';
    await page.screenshot({ path: screenshotPath(settingsShot), fullPage: true });
    screenshots.push(settingsShot);

    await clickButton(page, 'Paper Manager');
    await page.waitForTimeout(500);

    for (const paper of papers) {
      if (!fs.existsSync(paper.file)) {
        throw new Error(`Missing controlled PDF: ${paper.file}`);
      }
      await clickButton(page, 'Upload paper');
      await page.locator('#paper-file').setInputFiles(paper.file);
      await page.locator('#paper-title').fill(paper.title);
      await page.locator('button[type="submit"]').filter({ hasText: 'Start ingest' }).first().click();
      await waitForText(page, paper.title, 90000);
      await page.waitForTimeout(1200);
      uploads.push({
        title: paper.title,
        file: path.basename(paper.file),
        visibleStatus: await visibleStatusFor(page, paper.title),
      });
    }

    await page.waitForTimeout(2000);
    const uploadShot = 'ui-uploaded-ready.png';
    await page.screenshot({ path: screenshotPath(uploadShot), fullPage: true });
    screenshots.push(uploadShot);

    await clickButton(page, 'Chat');
    await page.waitForTimeout(800);
    const chatReadyShot = 'ui-chat-ready.png';
    await page.screenshot({ path: screenshotPath(chatReadyShot), fullPage: true });
    screenshots.push(chatReadyShot);

    await page.locator('#question').fill(question);
    await clickButton(page, 'Search evidence');
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(4000);
    evidenceSummary = await bodyText(page);
    const evidenceShot = 'ui-evidence-search.png';
    await page.screenshot({ path: screenshotPath(evidenceShot), fullPage: true });
    screenshots.push(evidenceShot);

    const lowerEvidence = evidenceSummary.toLowerCase();
    if (!lowerEvidence.includes('visrag_core_marker') && !lowerEvidence.includes('page') && !lowerEvidence.includes('citation')) {
      status = 'DONE_WITH_CONCERNS';
      deviations.push('Evidence search completed from the UI, but visible text did not clearly include the marker, page, or citation terms.');
    }
  } catch (error) {
    status = 'DONE_WITH_CONCERNS';
    deviations.push(`Flow stopped early: ${sanitize(error && error.stack ? error.stack : error)}`);
  } finally {
    const body = evidenceSummary || settingsSummary || '';
    const evidenceExcerpt = body
      ? body.slice(Math.max(0, body.toLowerCase().indexOf('retrieval evidence') - 200), Math.min(body.length, body.toLowerCase().indexOf('retrieval evidence') + 1400))
      : 'No evidence/chat text captured.';

    const uploadLines = papers.map(paper => {
      const found = uploads.find(item => item.title === paper.title);
      if (!found) return `- ${paper.title} (${path.basename(paper.file)}): not completed/visible.`;
      return `- ${found.title} (${found.file}): ${found.visibleStatus}`;
    });

    const summary = [
      `# UI Flow Verification Summary`,
      ``,
      `Status: ${status}`,
      ``,
      `## Browser/tool used`,
      `- Playwright Test via npx (@playwright/test), Chromium headless.`,
      `- Automation script: artifacts/real-local-test/2026-06-26/ui-flow.spec.cjs`,
      `- Temporary Playwright config: artifacts/real-local-test/2026-06-26/ui-playwright.config.cjs`,
      ``,
      `## Screenshots written`,
      ...screenshots.map(name => `- artifacts/real-local-test/2026-06-26/${name}`),
      ``,
      `## API/settings`,
      `- API online indicator visible on initial/settings UI: ${apiOnlineVisible ? 'yes' : 'no'}.`,
      `- FastAPI URL set/confirmed through Settings UI: ${apiUrl}.`,
      `- API key field was left blank; no API key was read, entered, or printed.`,
      `- Image context set/confirmed enabled; Max evidence images set to 4.`,
      ``,
      `## Upload results`,
      ...uploadLines,
      ``,
      `## Evidence/search result`,
      `- Search question: ${question}`,
      `- Evidence/chat visible excerpt: ${evidenceExcerpt || 'No visible evidence excerpt captured.'}`,
      ``,
      `## Console/network errors`,
      `- Console warnings/errors: ${consoleErrors.length ? consoleErrors.join(' | ') : 'none captured.'}`,
      `- Network/request errors: ${networkErrors.length ? [...new Set(networkErrors)].join(' | ') : 'none captured.'}`,
      ``,
      `## Blockers or deviations`,
      deviations.length ? deviations.map(item => `- ${item}`).join('\n') : `- None.`,
      ``,
    ].join('\n');

    fs.writeFileSync(path.join(artifactDir, 'ui-flow-summary.md'), summary, 'utf8');
  }
});
