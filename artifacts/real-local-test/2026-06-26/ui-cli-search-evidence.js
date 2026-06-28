async (page) => {
  const webUrl = "http://127.0.0.1:3000";
  const evidenceScreenshot =
    "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26\\ui-search-evidence.png";
  const previewScreenshot =
    "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26\\ui-evidence-preview.png";

  await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 });
  const chatTab = page.getByRole("tab", { name: /^Chat$/i });
  if (await chatTab.count()) {
    await chatTab.click();
  } else {
    await page.getByRole("button", { name: /^Chat$/i }).click();
  }

  await page.locator("#question").fill(
    "Which pages describe BM25 exact matching and malicious evidence text?",
  );
  const searchResponsePromise = page.waitForResponse(
    (response) => response.url().includes("/retrieval/search") && response.request().method() === "POST",
    { timeout: 90000 },
  );
  await page.getByRole("button", { name: /^Search evidence$/i }).click();
  const searchResponse = await searchResponsePromise;
  console.log(`SEARCH_STATUS ${searchResponse.status()}`);
  if (searchResponse.status() !== 200) {
    throw new Error(`Search evidence failed with ${searchResponse.status()}`);
  }

  await page.locator(".evidence-item").first().waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: evidenceScreenshot, fullPage: true });
  console.log(`SCREENSHOT ${evidenceScreenshot}`);

  await page.locator(".evidence-card-button").first().click();
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 30000 });
  await page.screenshot({ path: previewScreenshot, fullPage: true });
  console.log(`SCREENSHOT ${previewScreenshot}`);
}
