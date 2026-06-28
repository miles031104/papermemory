const { test } = require('@playwright/test');

test('recon upload modal', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle', timeout: 30000 });
  await page.locator('button').filter({ hasText: 'Paper Manager' }).first().click();
  await page.locator('button').filter({ hasText: 'Upload paper' }).first().click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: 'ui-upload-recon.png', fullPage: true });
  const info = await page.evaluate(() => {
    const textOf = el => (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ');
    return {
      text: (document.body.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 6000),
      controls: [...document.querySelectorAll('input,textarea,select,button')].map((el, i) => ({
        i,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        name: el.getAttribute('name') || '',
        id: el.id || '',
        aria: el.getAttribute('aria-label') || '',
        placeholder: el.getAttribute('placeholder') || '',
        label: el.labels && el.labels[0] ? el.labels[0].innerText.trim().replace(/\s+/g, ' ') : '',
        text: textOf(el).slice(0, 120),
      })).slice(0, 180),
    };
  });
  console.log(JSON.stringify(info, null, 2));
});
