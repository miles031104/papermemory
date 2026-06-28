const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const webUrl = "http://127.0.0.1:3000";
const apiUrl = "http://127.0.0.1:8000";
const outDir = "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26";
const screenshotPath = path.join(outDir, "ui-main-upload-missing-final.png");
const summaryPath = path.join(outDir, "ui-main-upload-missing-summary.md");

const uploads = [
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\bm25-exact.pdf",
    filename: "bm25-exact.pdf",
    title: "Real Test BM25 Exact",
    pageCount: 3,
  },
  {
    file: "D:\\codex\\llm_paper_assis\\papermemory\\tmp\\real-local-test-corpus\\agent-robustness.pdf",
    filename: "agent-robustness.pdf",
    title: "Real Test Agent Robustness",
    pageCount: 3,
  },
];

const consoleMessages = [];
const networkErrors = [];
const uploadResults = [];

function papersFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.papers)) return payload.papers;
  return [];
}

async function getPapers(request) {
  const response = await request.get(`${apiUrl}/papers`);
  const payload = await response.json();
  return {
    status: response.status(),
    papers: papersFromPayload(payload),
  };
}

function paperMatchesUpload(paper, upload) {
  return paper.filename === upload.filename && paper.status === "ready" && paper.page_count === upload.pageCount;
}

async function openUploadForm(page) {
  await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 });
  await page.getByRole("button", { name: /^Paper Manager$/i }).click();
  await page.waitForTimeout(500);
  const uploadPaper = page.getByRole("button", { name: /^Upload paper$/i });
  if (await uploadPaper.count()) {
    await uploadPaper.first().click();
  } else {
    await page.getByRole("button", { name: /^Upload first paper$/i }).click();
  }
  await page.locator("#paper-file").waitFor({ state: "attached", timeout: 10000 });
}

function writeSummary(finalPapers) {
  const lines = [
    "# Main Upload Missing Summary",
    "",
    "## Tool",
    "",
    "- Playwright `@playwright/test` spec run by the main controller.",
    "",
    "## Upload Attempts",
    "",
  ];

  for (const result of uploadResults) {
    lines.push(
      `- ${result.filename}: ${result.status}; post_status=${result.postStatus}; title_seen=${result.titleSeen}; paper_id=${result.paperId || "n/a"}`,
    );
  }

  lines.push("", "## Final Papers", "");
  for (const paper of finalPapers) {
    lines.push(
      `- ${paper.paper_id}: title=${paper.title}; filename=${paper.filename}; status=${paper.status}; pages=${paper.page_count}`,
    );
  }

  lines.push("", "## Console / Network Issues", "");
  if (consoleMessages.length === 0 && networkErrors.length === 0) {
    lines.push("- None captured except browser/devtool noise.");
  } else {
    for (const message of consoleMessages) lines.push(`- Console: ${message}`);
    for (const message of networkErrors) lines.push(`- Network: ${message}`);
  }

  lines.push("", "## Artifacts", "", `- Screenshot: \`${screenshotPath}\``);
  fs.writeFileSync(summaryPath, `${lines.join("\n")}\n`, "utf8");
}

test("upload missing controlled PDFs through UI", async ({ page, request }) => {
  test.setTimeout(360000);

  for (const upload of uploads) {
    if (!fs.existsSync(upload.file)) {
      throw new Error(`Missing test PDF: ${upload.file}`);
    }
  }

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push(`${message.type()}: ${message.text()}`);
    }
  });
  page.on("requestfailed", (requestInfo) => {
    networkErrors.push(`${requestInfo.method()} ${requestInfo.url()} :: ${requestInfo.failure()?.errorText || "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400 && !response.url().endsWith("/favicon.ico")) {
      networkErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  try {
    for (const upload of uploads) {
      const before = await getPapers(request);
      const alreadyReady = before.papers.find((paper) => paperMatchesUpload(paper, upload));
      if (alreadyReady) {
        uploadResults.push({
          filename: upload.filename,
          status: "already ready",
          postStatus: "skipped",
          titleSeen: alreadyReady.title === upload.title,
          paperId: alreadyReady.paper_id,
        });
        continue;
      }

      await openUploadForm(page);
      await page.locator("#paper-file").setInputFiles(upload.file);
      await page.locator("#paper-title").fill("");
      await page.locator("#paper-title").fill(upload.title);

      const formState = await page.evaluate(() => {
        const fileInput = document.querySelector("#paper-file");
        const titleInput = document.querySelector("#paper-title");
        const submit = Array.from(document.querySelectorAll("button")).find((button) =>
          /start ingest/i.test(button.textContent || ""),
        );
        return {
          selectedFileName: fileInput && fileInput.files && fileInput.files[0] ? fileInput.files[0].name : null,
          titleValue: titleInput ? titleInput.value : null,
          submitDisabled: submit ? submit.disabled : null,
        };
      });

      expect(formState.selectedFileName).toBe(upload.filename);
      expect(formState.titleValue).toBe(upload.title);
      expect(formState.submitDisabled).toBe(false);

      const uploadResponsePromise = page.waitForResponse(
        (response) => response.url().includes("/papers/upload") && response.request().method() === "POST",
        { timeout: 90000 },
      );
      await page.getByRole("button", { name: /^Start ingest$/i }).click();
      const uploadResponse = await uploadResponsePromise;
      expect(uploadResponse.status()).toBe(201);

      let finalMatch = null;
      const deadline = Date.now() + 120000;
      while (Date.now() < deadline) {
        const current = await getPapers(request);
        finalMatch = current.papers.find((paper) => paperMatchesUpload(paper, upload));
        if (finalMatch) break;
        await page.waitForTimeout(2000);
      }

      if (!finalMatch) {
        throw new Error(`Uploaded ${upload.filename}, but ready paper did not appear in /papers.`);
      }

      uploadResults.push({
        filename: upload.filename,
        status: "ready",
        postStatus: uploadResponse.status(),
        titleSeen: finalMatch.title === upload.title,
        paperId: finalMatch.paper_id,
      });
    }
  } finally {
    await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 }).catch(() => {});
    await page.getByRole("button", { name: /^Paper Manager$/i }).click().catch(() => {});
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    const final = await getPapers(request).catch(() => ({ papers: [] }));
    writeSummary(final.papers);
  }

  const final = await getPapers(request);
  for (const upload of uploads) {
    expect(final.papers.some((paper) => paperMatchesUpload(paper, upload))).toBe(true);
  }
});
