import { defineConfig, devices } from "@playwright/test";

const testPort = process.env.OMR_TEST_PORT || "18080";
const baseURL = process.env.BASE_URL || `http://127.0.0.1:${testPort}`;

export default defineConfig({
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
  ],
  use: {
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "api",
      testDir: "./tests/api",
      use: {
        baseURL,
        extraHTTPHeaders: {
          Accept: "application/json",
        },
      },
    },
    {
      name: "e2e",
      testDir: "./tests/e2e",
      use: {
        ...devices["Desktop Chrome"],
        baseURL,
        acceptDownloads: true,
      },
    },
  ],
  webServer: [
    {
      command: "npm run build",
      cwd: "./frontend",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        process.platform === "win32"
          ? ".venv\\Scripts\\python.exe scripts/start_test_server.py"
          : ".venv/bin/python scripts/start_test_server.py",
      cwd: ".",
      url: `${baseURL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
