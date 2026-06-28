module.exports = {
  testDir: "D:/codex/llm_paper_assis/papermemory/artifacts/real-local-test/2026-06-26",
  testMatch: /ui-main-upload-missing\.spec\.cjs/,
  reporter: [["line"]],
  outputDir: "D:/codex/llm_paper_assis/papermemory/artifacts/real-local-test/2026-06-26/ui-main-upload-missing-results",
  workers: 1,
  use: {
    browserName: "chromium",
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
};
