import { defineConfig, devices } from "@playwright/test";

// Admin Web E2E. Runs the real portal (Vite) against the isolated fixture API
// (a dedicated SQLite file built by e2e/start-api.mjs). Tests mutate shared
// state, so they run serially on one worker. See docs/testing/test-data-plan.md.
const apiPort = process.env.E2E_API_PORT ?? "8010";
const webPort = process.env.E2E_WEB_PORT ?? "5174";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: `http://127.0.0.1:${webPort}/portal/`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "node e2e/start-api.mjs",
      url: `http://127.0.0.1:${apiPort}/v1/public/health`,
      timeout: 180_000,
      reuseExistingServer: !!process.env.E2E_REUSE,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${webPort} --strictPort`,
      url: `http://127.0.0.1:${webPort}/portal/`,
      timeout: 60_000,
      reuseExistingServer: !!process.env.E2E_REUSE,
      env: { VITE_API_TARGET: `http://127.0.0.1:${apiPort}` },
    },
  ],
});
