const fs = require("fs");
const { chromium } = require("playwright");

const webUrl = "http://127.0.0.1:3000";
const screenshotPath =
  "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26\\ui-chat-live-answer.png";
const summaryPath =
  "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26\\ui-chat-live-smoke-summary.json";

const modelSettings = {
  provider: "openai-compatible",
  providerCompany: "Custom",
  baseUrl: "https://api.minimax.io/v1",
  model: "MiniMax-M3",
  apiKey: "",
  temperature: 0.2,
  retrievalTopK: 6,
  requireEvidence: true,
  useMultimodalContext: true,
  maxEvidenceImages: 4,
};

const installSettings = {
  mode: "custom",
  apiBaseUrl: "http://127.0.0.1:8000",
  qdrantUrl: "http://localhost:6333",
  storageRoot: "./storage",
  hfToken: "",
  visragModel: "openbmb/VisRAG-Ret",
  visragBackend: "stub",
  visragDevice: "auto",
  visragDtype: "auto",
  trustRemoteCode: false,
  qdrantVectorSize: 8,
  useMultimodalContext: true,
  maxEvidenceImages: 4,
  providerCompany: "Custom",
  providerBaseUrl: "https://api.minimax.io/v1",
  providerModel: "MiniMax-M3",
  providerApiKey: "",
};

function sanitize(text) {
  return String(text || "")
    .replace(/[A-Za-z0-9_-]{32,}/g, "[redacted-long-token]")
    .replace(/\s+/g, " ")
    .trim();
}

async function maybeClick(locator) {
  if ((await locator.count()) > 0) {
    await locator.first().click();
    return true;
  }
  return false;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const consoleMessages = [];
  const requestFailures = [];
  const chatResponses = [];

  page.on("console", (msg) => {
    if (["error", "warning"].includes(msg.type())) {
      consoleMessages.push(sanitize(`${msg.type()}: ${msg.text()}`));
    }
  });
  page.on("requestfailed", (req) =>
    requestFailures.push(sanitize(`${req.method()} ${req.url()} ${req.failure()?.errorText || ""}`)),
  );
  page.on("response", (response) => {
    if (response.url().includes("/chat")) {
      chatResponses.push({
        url: sanitize(response.url()),
        status: response.status(),
        contentType: response.headers()["content-type"] || "",
      });
    }
  });

  await page.addInitScript(
    ({ modelSettings, installSettings }) => {
      window.localStorage.setItem("papermemory.modelSettings.v1", JSON.stringify(modelSettings));
      window.localStorage.setItem("papermemory.installSettings.v1", JSON.stringify(installSettings));
    },
    { modelSettings, installSettings },
  );

  try {
    await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 });
    const chatTab = page.getByRole("tab", { name: /^Chat$/i });
    if (!(await maybeClick(chatTab))) {
      await page.getByRole("button", { name: /^Chat$/i }).click();
    }

    await page.getByRole("button", { name: /^Clear$/i }).click();
    await page.locator("#question").fill(
      "In one concise answer, compare VisRAG page-image search with BM25 exact matching and cite pages.",
    );

    const chatResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/chat?stream=true") && response.request().method() === "POST",
      { timeout: 120000 },
    );
    await page.getByRole("button", { name: /^Ask$/i }).click();
    const chatResponse = await chatResponsePromise;

    await page
      .locator(".message--assistant .message__body--markdown")
      .filter({ hasText: /VisRAG|BM25|page-image|exact/i })
      .last()
      .waitFor({ state: "visible", timeout: 180000 });
    await page.locator(".citation-chip").first().waitFor({ state: "visible", timeout: 30000 });
    await page.locator(".evidence-item").first().waitFor({ state: "visible", timeout: 30000 });

    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const summary = await page.evaluate(() => {
      const textOf = (selector) =>
        [...document.querySelectorAll(selector)]
          .map((el) => (el.innerText || el.textContent || "").trim().replace(/\s+/g, " "))
          .filter(Boolean);
      const assistantMessages = textOf(".message--assistant .message__body");
      const latestAssistant = assistantMessages[assistantMessages.length - 1] || "";
      return {
        visibleTextPrefix: (document.body.innerText || "").trim().replace(/\s+/g, " ").slice(0, 1200),
        latestAssistantPrefix: latestAssistant.slice(0, 1200),
        citationChipCount: document.querySelectorAll(".citation-chip").length,
        evidenceItemCount: document.querySelectorAll(".evidence-item").length,
        inlineErrors: textOf('[role="alert"], .inline-alert--error'),
      };
    });

    const payload = {
      status: "success",
      chatResponseStatus: chatResponse.status(),
      chatResponses,
      screenshotPath,
      summary,
      consoleMessages: consoleMessages.slice(-20),
      requestFailures,
    };
    fs.writeFileSync(summaryPath, JSON.stringify(payload, null, 2), "utf8");
    console.log(JSON.stringify(payload, null, 2));

    if (chatResponse.status() !== 200) {
      throw new Error(`Chat stream returned HTTP ${chatResponse.status()}`);
    }
    if (!/VisRAG|page-image/i.test(summary.latestAssistantPrefix)) {
      throw new Error("Assistant answer did not mention VisRAG/page-image behavior.");
    }
    if (!/BM25|exact/i.test(summary.latestAssistantPrefix)) {
      throw new Error("Assistant answer did not mention BM25/exact matching.");
    }
    if (summary.citationChipCount < 1 || summary.evidenceItemCount < 1) {
      throw new Error("UI did not render citation chips and evidence cards.");
    }
    if (summary.inlineErrors.length > 0) {
      throw new Error(`UI rendered inline errors: ${summary.inlineErrors.join(" | ")}`);
    }
  } catch (error) {
    const payload = {
      status: "error",
      error: sanitize(error instanceof Error ? error.message : String(error)),
      chatResponses,
      screenshotPath,
      consoleMessages: consoleMessages.slice(-20),
      requestFailures,
    };
    fs.writeFileSync(summaryPath, JSON.stringify(payload, null, 2), "utf8");
    console.log(JSON.stringify(payload, null, 2));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
