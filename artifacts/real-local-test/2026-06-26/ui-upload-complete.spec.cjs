const fs = require("fs");
const path = require("path");
const { test } = require("@playwright/test");

const webUrl = "http://127.0.0.1:3000";
const apiUrl = "http://127.0.0.1:8000";
const outDir = "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26";
const screenshotPath = path.join(outDir, "ui-upload-complete.png");
const summaryPath = path.join(outDir, "ui-upload-worker-summary.md");

const uploads = [
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\visrag-core.pdf",
    title: "Real Test VisRAG Core",
  },
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\bm25-exact.pdf",
    title: "Real Test BM25 Exact",
  },
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\agent-robustness.pdf",
    title: "Real Test Agent Robustness",
  },
];

const consoleMessages = [];
const networkErrors = [];
const uploadResults = [];

function papersFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.papers)) return payload.papers;
  if (payload && Array.isArray(payload.items)) return payload.items;
  return [];
}

function paperTitle(paper) {
  return paper.title || paper.name || paper.display_title || "";
}

function paperStatus(paper) {
  return paper.status || paper.ingest_status || paper.state || paper.processing_status || "unknown";
}

async function getPapers(request) {
  const response = await request.get(`${apiUrl}/papers`);
  const text = await response.text();
  let payload;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = { parseError: text.slice(0, 500) };
  }
  return {
    ok: response.ok(),
    status: response.status(),
    payload,
    papers: papersFromPayload(payload),
  };
}

async function ensurePaperManager(page) {
  await page.goto(webUrl, { waitUntil: "networkidle" });
  const paperManager = page.getByRole("button", { name: /paper manager/i });
  if (await paperManager.count()) {
    await paperManager.first().click();
  } else {
    await page.getByText(/paper manager/i).first().click();
  }
  await page.waitForTimeout(500);
}

async function ensureUploadForm(page) {
  const fileInput = page.locator("#paper-file");
  if (await fileInput.isVisible().catch(() => false)) return;

  const uploadPaper = page.getByRole("button", { name: /upload paper/i });
  if (await uploadPaper.count()) {
    await uploadPaper.first().click();
  } else {
    const uploadFirst = page.getByRole("button", { name: /upload first paper/i });
    if (await uploadFirst.count()) {
      await uploadFirst.first().click();
    } else {
      await page.getByText(/upload/i).first().click();
    }
  }
  await fileInput.waitFor({ state: "attached", timeout: 5000 });
}

async function waitForTitle(page, request, title) {
  const deadline = Date.now() + 120000;
  let lastPapers = [];
  let lastStatus = "not_checked";
  let visibleInUi = false;

  while (Date.now() < deadline) {
    const api = await getPapers(request).catch((error) => ({
      ok: false,
      status: "request_error",
      payload: { error: String(error) },
      papers: [],
    }));
    lastPapers = api.papers;
    lastStatus = String(api.status);

    const match = lastPapers.find((paper) => paperTitle(paper) === title);
    if (match) {
      return { ready: true, source: "api", paper: match, apiStatus: lastStatus, papers: lastPapers };
    }

    visibleInUi = await page.getByText(title, { exact: true }).isVisible().catch(() => false);
    if (visibleInUi) {
      return { ready: true, source: "ui", paper: null, apiStatus: lastStatus, papers: lastPapers };
    }

    await page.waitForTimeout(2000);
  }

  return { ready: false, source: visibleInUi ? "ui" : "timeout", paper: null, apiStatus: lastStatus, papers: lastPapers };
}

function writeSummary(initial, final) {
  const lines = [];
  lines.push("# UI Upload Worker Summary");
  lines.push("");
  lines.push("## Commands / Tool Used");
  lines.push("");
  lines.push("- Tool: Playwright via temporary `@playwright/test` spec.");
  lines.push("- Command: `npx --yes --package @playwright/test playwright test artifacts/real-local-test/2026-06-26/ui-upload-complete.spec.cjs --headed --project=chromium --reporter=line`");
  lines.push("- Web: `http://127.0.0.1:3000`");
  lines.push("- API: `http://127.0.0.1:8000`");
  lines.push("");
  lines.push("## Upload Results");
  lines.push("");
  for (const result of uploadResults) {
    lines.push(`- ${result.title}: ${result.ready ? "ready" : "not ready"} via ${result.source}; API status ${result.apiStatus}; paper status ${result.status}; file \`${result.file}\``);
  }
  for (const upload of uploads.slice(uploadResults.length)) {
    lines.push(`- ${upload.title}: not attempted because an earlier upload did not become ready; file \`${upload.file}\``);
  }
  lines.push("");
  lines.push("## Final /papers");
  lines.push("");
  lines.push(`- Initial /papers count: ${initial.papers.length} (HTTP ${initial.status})`);
  lines.push(`- Final /papers count: ${final.papers.length} (HTTP ${final.status})`);
  for (const paper of final.papers) {
    lines.push(`- ${paperTitle(paper) || "(untitled)"}: ${paperStatus(paper)}`);
  }
  lines.push("");
  lines.push("## Console / Network Errors");
  lines.push("");
  if (consoleMessages.length === 0 && networkErrors.length === 0) {
    lines.push("- None captured.");
  } else {
    for (const message of consoleMessages) lines.push(`- Console: ${message}`);
    for (const message of networkErrors) lines.push(`- Network: ${message}`);
  }
  lines.push("");
  lines.push("## Artifacts");
  lines.push("");
  lines.push(`- Screenshot: \`${screenshotPath}\``);

  fs.writeFileSync(summaryPath, `${lines.join("\n")}\n`, "utf8");
}

test("complete UI upload flow", async ({ page, request }) => {
  test.setTimeout(420000);

  for (const upload of uploads) {
    if (!fs.existsSync(upload.file)) {
      throw new Error(`Missing PDF: ${upload.file}`);
    }
  }

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push(`${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => {
    consoleMessages.push(`pageerror: ${error.message}`);
  });
  page.on("requestfailed", (requestInfo) => {
    networkErrors.push(`${requestInfo.method()} ${requestInfo.url()} :: ${requestInfo.failure()?.errorText || "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      networkErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  await ensurePaperManager(page);
  const initial = await getPapers(request);
  let final = initial;

  try {
    for (const upload of uploads) {
      await ensureUploadForm(page);
      await page.locator("#paper-file").setInputFiles(upload.file);
      await page.locator("#paper-title").fill(upload.title);
      await page.getByRole("button", { name: /start ingest/i }).click();

      const result = await waitForTitle(page, request, upload.title);
      uploadResults.push({
        title: upload.title,
        file: upload.file,
        ready: result.ready,
        source: result.source,
        apiStatus: result.apiStatus,
        status: result.paper ? paperStatus(result.paper) : "unknown",
      });

      if (!result.ready) break;
    }
  } finally {
    await ensurePaperManager(page).catch(() => {});
    final = await getPapers(request).catch(() => final);
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    writeSummary(initial, final);
  }

  const missing = uploads.filter((upload) => !final.papers.some((paper) => paperTitle(paper) === upload.title));
  if (missing.length) {
    throw new Error(`DONE_WITH_CONCERNS missing=${missing.map((item) => item.title).join(", ")}`);
  }
});
