const fs = require("fs");
const path = require("path");
const { test } = require("@playwright/test");

const webUrl = "http://127.0.0.1:3000";
const apiUrl = "http://127.0.0.1:8000";
const outDir = "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26";
const summaryPath = path.join(outDir, "ui-upload-remaining-summary.md");

const requiredTitles = [
  "Real Test VisRAG Core",
  "Real Test BM25 Exact",
  "Real Test Agent Robustness",
];

const uploads = [
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\bm25-exact.pdf",
    title: "Real Test BM25 Exact",
    screenshot: path.join(outDir, "ui-upload-remaining-bm25.png"),
    dom: path.join(outDir, "ui-upload-remaining-bm25-dom.txt"),
  },
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\agent-robustness.pdf",
    title: "Real Test Agent Robustness",
    screenshot: path.join(outDir, "ui-upload-remaining-agent-robustness.png"),
    dom: path.join(outDir, "ui-upload-remaining-agent-robustness-dom.txt"),
  },
];

const finalScreenshot = path.join(outDir, "ui-upload-remaining-final.png");
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

function readyPaper(papers, title) {
  return papers.find((paper) => paperTitle(paper) === title && paperStatus(paper) === "ready") || null;
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

async function clickPaperManager(page) {
  const button = page.getByRole("button", { name: /paper manager/i });
  if (await button.count()) {
    await button.first().click();
    return;
  }
  await page.getByText(/paper manager/i).first().click();
}

async function openUploadForm(page) {
  const uploadPaper = page.getByRole("button", { name: /^upload paper$/i });
  if (await uploadPaper.count()) {
    await uploadPaper.first().click();
  } else {
    const uploadFirst = page.getByRole("button", { name: /upload first paper/i });
    if (await uploadFirst.count()) {
      await uploadFirst.first().click();
    } else {
      await page.getByRole("button", { name: /upload/i }).first().click();
    }
  }

  const fileInput = page.locator("#paper-file");
  await fileInput.waitFor({ state: "attached", timeout: 10000 });
  await fileInput.waitFor({ state: "visible", timeout: 10000 }).catch(() => {});
  await fileInput.evaluate((input) => {
    if (input.disabled) throw new Error("#paper-file is disabled");
  });
}

async function waitForReadyOrUploadResponse(page, request, title, uploadResponsePromise) {
  const deadline = Date.now() + 120000;
  let uploadResponseStatus = null;
  let uploadResponseSeen = false;
  let lastPapers = [];

  const observedUpload = uploadResponsePromise.then((response) => {
    uploadResponseSeen = true;
    uploadResponseStatus = response.status();
    return response;
  }).catch((error) => {
    networkErrors.push(`Upload response wait failed for ${title}: ${error.message}`);
    return null;
  });

  while (Date.now() < deadline) {
    const response = await Promise.race([
      observedUpload,
      page.waitForTimeout(500).then(() => null),
    ]);
    if (response && response.status() === 201) {
      const api = await getPapers(request);
      lastPapers = api.papers;
      const match = readyPaper(lastPapers, title);
      if (match) {
        return {
          ok: true,
          source: "upload_response_and_api_ready",
          uploadResponseStatus,
          paper: match,
          papers: lastPapers,
        };
      }
    }

    const api = await getPapers(request);
    lastPapers = api.papers;
    const match = readyPaper(lastPapers, title);
    if (match) {
      return {
        ok: true,
        source: uploadResponseSeen ? "api_ready_after_upload_response" : "api_ready",
        uploadResponseStatus,
        paper: match,
        papers: lastPapers,
      };
    }
  }

  return {
    ok: false,
    source: uploadResponseSeen ? "upload_seen_but_not_ready" : "timeout",
    uploadResponseStatus,
    paper: null,
    papers: lastPapers,
  };
}

async function uploadOne(context, upload) {
  const page = await context.newPage();
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push(`${upload.title}: console ${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => {
    consoleMessages.push(`${upload.title}: pageerror: ${error.message}`);
  });
  page.on("requestfailed", (requestInfo) => {
    networkErrors.push(`${upload.title}: ${requestInfo.method()} ${requestInfo.url()} :: ${requestInfo.failure()?.errorText || "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      networkErrors.push(`${upload.title}: ${response.status()} ${response.url()}`);
    }
  });

  try {
    await page.goto(webUrl, { waitUntil: "networkidle" });
    await clickPaperManager(page);
    await openUploadForm(page);

    const fileInput = page.locator("#paper-file");
    const titleInput = page.locator("#paper-title");
    const startButton = page.getByRole("button", { name: /start ingest/i });

    await fileInput.setInputFiles(upload.file);
    await titleInput.fill(upload.title);

    const disabled = await startButton.isDisabled();
    if (disabled) {
      await page.screenshot({ path: upload.screenshot, fullPage: true });
      fs.writeFileSync(upload.dom, await page.content(), "utf8");
      return {
        title: upload.title,
        file: upload.file,
        ok: false,
        source: "start_ingest_disabled",
        uploadResponseStatus: null,
        paperStatus: "not_submitted",
        screenshot: upload.screenshot,
        dom: upload.dom,
      };
    }

    const uploadResponsePromise = page.waitForResponse((response) => (
      response.url().includes("/papers/upload") &&
      response.request().method() === "POST"
    ), { timeout: 120000 });

    await startButton.click();
    const result = await waitForReadyOrUploadResponse(page, context.request, upload.title, uploadResponsePromise);
    await page.screenshot({ path: upload.screenshot, fullPage: true });

    return {
      title: upload.title,
      file: upload.file,
      ok: result.ok,
      source: result.source,
      uploadResponseStatus: result.uploadResponseStatus,
      paperStatus: result.paper ? paperStatus(result.paper) : "missing_or_not_ready",
      screenshot: upload.screenshot,
      dom: "",
    };
  } finally {
    await page.close().catch(() => {});
  }
}

function writeSummary(initial, final, accepted) {
  const lines = [];
  lines.push("# UI Upload Remaining Summary");
  lines.push("");
  lines.push(`- Result: ${accepted ? "DONE" : "DONE_WITH_CONCERNS"}`);
  lines.push(`- Web: ${webUrl}`);
  lines.push(`- API: ${apiUrl}`);
  lines.push("");
  lines.push("## Upload Attempts");
  lines.push("");
  for (const result of uploadResults) {
    lines.push(`- ${result.title}: ${result.ok ? "success" : "concern"}; source=${result.source}; upload_response=${result.uploadResponseStatus ?? "not_seen"}; final_status=${result.paperStatus}; screenshot=${result.screenshot}`);
    if (result.dom) lines.push(`- ${result.title} DOM state: ${result.dom}`);
  }
  lines.push("");
  lines.push("## Final /papers");
  lines.push("");
  lines.push(`- Initial /papers count: ${initial.papers.length} (HTTP ${initial.status})`);
  lines.push(`- Final /papers count: ${final.papers.length} (HTTP ${final.status})`);
  for (const paper of final.papers) {
    lines.push(`- ${paperTitle(paper) || "(untitled)"}: ${paperStatus(paper)}; filename=${paper.filename || paper.file_name || "unknown"}; page_count=${paper.page_count ?? "unknown"}`);
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
  for (const result of uploadResults) {
    lines.push(`- ${result.screenshot}`);
  }
  lines.push(`- ${finalScreenshot}`);
  fs.writeFileSync(summaryPath, `${lines.join("\n")}\n`, "utf8");
}

test("upload remaining PDFs through the UI", async ({ browser, request }) => {
  test.setTimeout(360000);

  for (const upload of uploads) {
    if (!fs.existsSync(upload.file)) {
      throw new Error(`Missing PDF: ${upload.file}`);
    }
  }

  const context = await browser.newContext();
  context.request = request;
  let initial = { status: "not_checked", papers: [] };
  let final = { status: "not_checked", papers: [] };

  try {
    initial = await getPapers(context.request);

    for (const upload of uploads) {
      const existing = readyPaper((await getPapers(context.request)).papers, upload.title);
      if (existing) {
        const page = await context.newPage();
        await page.goto(webUrl, { waitUntil: "networkidle" });
        await clickPaperManager(page);
        await page.screenshot({ path: upload.screenshot, fullPage: true });
        await page.close().catch(() => {});
        uploadResults.push({
          title: upload.title,
          file: upload.file,
          ok: true,
          source: "already_ready_before_attempt",
          uploadResponseStatus: null,
          paperStatus: paperStatus(existing),
          screenshot: upload.screenshot,
          dom: "",
        });
        continue;
      }

      const result = await uploadOne(context, upload);
      uploadResults.push(result);
      if (!result.ok) break;
    }

    const finalPage = await context.newPage();
    await finalPage.goto(webUrl, { waitUntil: "networkidle" });
    await clickPaperManager(finalPage);
    await finalPage.screenshot({ path: finalScreenshot, fullPage: true });
    await finalPage.close().catch(() => {});

    final = await getPapers(context.request);
    const accepted = requiredTitles.every((title) => readyPaper(final.papers, title));
    writeSummary(initial, final, accepted);

    if (!accepted) {
      const statuses = requiredTitles.map((title) => {
        const match = final.papers.find((paper) => paperTitle(paper) === title);
        return `${title}=${match ? paperStatus(match) : "missing"}`;
      }).join("; ");
      throw new Error(`DONE_WITH_CONCERNS ${statuses}`);
    }

    console.log("DONE");
  } finally {
    await context.close().catch(() => {});
  }
});
