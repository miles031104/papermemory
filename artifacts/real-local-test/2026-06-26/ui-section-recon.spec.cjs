const { test } = require('@playwright/test');

test('recon settings and manager', async ({ page }) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle', timeout: 30000 });

  async function dump(name) {
    const info = await page.evaluate(() => {
      const summarize = el => {
        const rect = el.getBoundingClientRect();
        const label = el.labels && el.labels[0] ? el.labels[0].innerText : '';
        return {
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute('type') || '',
          name: el.getAttribute('name') || '',
          id: el.id || '',
          aria: el.getAttribute('aria-label') || '',
          placeholder: el.getAttribute('placeholder') || '',
          label: (label || '').trim().replace(/\s+/g, ' '),
          visible: rect.width > 0 && rect.height > 0,
        };
      };
      return {
        text: (document.body.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 6000),
        controls: [...document.querySelectorAll('input,textarea,select,button')].map(summarize).slice(0, 160),
      };
    });
    console.log(`--- ${name} ---`);
    console.log(JSON.stringify(info, null, 2));
    await page.screenshot({ path: `ui-${name}.png`, fullPage: true });
  }

  await page.getByRole('button', { name: /^Settings$/ }).first().click();
  await page.waitForTimeout(800);
  await dump('settings-recon');

  await page.locator('button').filter({ hasText: 'Paper Manager' }).first().click();
  await page.waitForTimeout(800);
  await dump('manager-recon');

  await page.locator('button').filter({ hasText: 'Chat' }).first().click();
  await page.waitForTimeout(800);
  await dump('chat-recon');
});
