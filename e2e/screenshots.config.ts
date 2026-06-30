import { defineConfig, devices } from "@playwright/test";

/**
 * Config dédiée à la **capture d'écrans** (app + vitrine), hors CI.
 * Boote la stack keyless : API sqlite seedée, frontend (preview 4173),
 * vitrine Astro (preview 4321). Lancer :
 *   PW_EXECUTABLE=<chromium> npx playwright test --config screenshots.config.ts
 */
const API = "http://localhost:8000";
const APP = "http://localhost:4173";
const SITE = "http://localhost:4321";
const DB = "sqlite+aiosqlite:///./shots.db";

export default defineConfig({
  testDir: "./screenshots",
  timeout: 300_000,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: APP,
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    launchOptions: process.env.PW_EXECUTABLE
      ? { executablePath: process.env.PW_EXECUTABLE }
      : {},
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "rm -f shots.db && python -m app.db.create_all && python -m app.db.seed && " +
        "uvicorn app.main:app --host 0.0.0.0 --port 8000",
      cwd: "../backend",
      url: `${API}/health`,
      timeout: 120_000,
      reuseExistingServer: true,
      env: {
        DATABASE_URL: DB,
        ENV: "local",
        CORS_ORIGINS: `["${APP}"]`,
        RATE_LIMIT_ENABLED: "false",
        SEED_DIR: "../data/seeds",
      },
    },
    {
      command: "npm run build && npm run preview -- --port 4173 --host",
      cwd: "../frontend",
      url: APP,
      timeout: 120_000,
      reuseExistingServer: true,
      env: { VITE_API_BASE_URL: `${API}/api/v1` },
    },
    {
      command: "npm run build && npm run preview -- --port 4321 --host",
      cwd: "../website",
      url: SITE,
      timeout: 120_000,
      reuseExistingServer: true,
      env: { PUBLIC_APP_URL: APP },
    },
  ],
});
