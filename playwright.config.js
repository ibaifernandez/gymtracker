const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  reporter: "list",
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:5055",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command:
      "rm -f .tmp/e2e/tracker-e2e.db .tmp/e2e/tracker-e2e.db-shm .tmp/e2e/tracker-e2e.db-wal && rm -rf .tmp/e2e/uploads && mkdir -p .tmp/e2e/uploads && PY=.venv/bin/python; if [ ! -x \"$PY\" ]; then PY=python3; fi; TRACKER_PORT=5055 TRACKER_DB_PATH=.tmp/e2e/tracker-e2e.db TRACKER_UPLOAD_ROOT=.tmp/e2e/uploads \"$PY\" app.py",
    url: "http://127.0.0.1:5055/",
    timeout: 120_000,
    reuseExistingServer: false,
  },
});
