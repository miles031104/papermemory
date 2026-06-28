module.exports = {
  testDir: '.',
  testMatch: /ui-.*\.spec\.cjs/,
  reporter: [['line']],
  outputDir: 'ui-test-results',
  workers: 1,
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
};
