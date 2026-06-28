async (page) => {
  const webUrl = "http://127.0.0.1:3000";
  const apiUrl = "http://127.0.0.1:8000";
  const screenshotPath =
    "D:\\codex\\llm_paper_assis\\papermemory\\artifacts\\real-local-test\\2026-06-26\\ui-cli-upload-missing-final.png";
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

  async function getPapers() {
    const result = await page.evaluate(async (url) => {
      const response = await fetch(`${url}/papers`);
      const payload = await response.json();
      return { ok: response.ok, status: response.status, payload };
    }, apiUrl);
    if (!result.ok) throw new Error(`GET /papers failed: ${result.status}`);
    return Array.isArray(result.payload.papers) ? result.payload.papers : [];
  }

  function matchesUpload(paper, upload) {
    return (
      paper.filename === upload.filename &&
      paper.status === "ready" &&
      paper.page_count === upload.pageCount
    );
  }

  async function waitForReady(upload) {
    const deadline = Date.now() + 120000;
    while (Date.now() < deadline) {
      const papers = await getPapers();
      const match = papers.find((paper) => matchesUpload(paper, upload));
      if (match) return match;
      await page.waitForTimeout(2000);
    }
    throw new Error(`Timed out waiting for ready paper ${upload.filename}`);
  }

  async function openUploadForm() {
    await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 });
    const manager = page.getByRole("tab", { name: /^Paper Manager$/i });
    if (await manager.count()) {
      await manager.click();
    } else {
      await page.getByRole("button", { name: /^Paper Manager$/i }).click();
    }
    await page.waitForTimeout(500);
    const uploadButton = page.getByRole("button", { name: /^Upload paper$/i });
    if (await uploadButton.count()) {
      await uploadButton.first().click();
    } else {
      await page.getByRole("button", { name: /^Upload first paper$/i }).click();
    }
    await page.locator("#paper-file").waitFor({ state: "attached", timeout: 10000 });
  }

  for (const upload of uploads) {
    const existing = (await getPapers()).find((paper) => matchesUpload(paper, upload));
    if (existing) {
      console.log(`SKIP ${upload.filename}: already ready as ${existing.paper_id}`);
      continue;
    }

    await openUploadForm();
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
    console.log(`FORM ${upload.filename}: ${JSON.stringify(formState)}`);
    if (formState.selectedFileName !== upload.filename) {
      throw new Error(`Wrong selected file: expected ${upload.filename}, got ${formState.selectedFileName}`);
    }
    if (formState.titleValue !== upload.title) {
      throw new Error(`Wrong title value: expected ${upload.title}, got ${formState.titleValue}`);
    }
    if (formState.submitDisabled) {
      throw new Error(`Start ingest disabled for ${upload.filename}`);
    }

    const uploadResponsePromise = page.waitForResponse(
      (response) => response.url().includes("/papers/upload") && response.request().method() === "POST",
      { timeout: 90000 },
    );
    await page.getByRole("button", { name: /^Start ingest$/i }).click();
    const uploadResponse = await uploadResponsePromise;
    console.log(`POST ${upload.filename}: ${uploadResponse.status()}`);
    if (uploadResponse.status() !== 201) {
      throw new Error(`Upload POST failed for ${upload.filename}: ${uploadResponse.status()}`);
    }
    const ready = await waitForReady(upload);
    console.log(`READY ${upload.filename}: ${ready.paper_id} title=${ready.title}`);
  }

  await page.goto(webUrl, { waitUntil: "networkidle", timeout: 30000 });
  const manager = page.getByRole("tab", { name: /^Paper Manager$/i });
  if (await manager.count()) await manager.click();
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`SCREENSHOT ${screenshotPath}`);
}
