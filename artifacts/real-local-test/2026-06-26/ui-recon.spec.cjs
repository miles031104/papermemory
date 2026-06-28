const { test } = require('@playwright/test');

test('recon visible PaperMemory UI', async ({ page }) => {
  const consoleMessages = [];
  const failures = [];
  page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`));
  page.on('requestfailed', req => failures.push(`${req.method()} ${req.url()} ${req.failure()?.errorText || ''}`));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle', timeout: 30000 });
  await page.screenshot({ path: 'artifacts/real-local-test/2026-06-26/ui-recon.png', fullPage: true });
  const snapshot = await page.evaluate(() => {
    const textOf = el => (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ');
    return {
      title: document.title,
      visibleText: (document.body.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 4000),
      buttons: [...document.querySelectorAll('button,[role="button"],a,[role="tab"]')].map((el, i) => ({
        i,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        aria: el.getAttribute('aria-label') || '',
        text: textOf(el).slice(0, 120),
      })).filter(x => x.text || x.aria).slice(0, 120),
      inputs: [...document.querySelectorAll('input,textarea,select')].map((el, i) => ({
        i,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        name: el.getAttribute('name') || '',
        id: el.id || '',
        aria: el.getAttribute('aria-label') || '',
        placeholder: el.getAttribute('placeholder') || '',
      })).slice(0, 80),
    };
  });
  console.log(JSON.stringify({ snapshot, consoleMessages, failures }, null, 2));
});
