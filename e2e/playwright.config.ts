import { defineConfig, devices } from "@playwright/test";

/**
 * E2E MyHanout — parcours critiques (Brique 8).
 *
 * `webServer` boote la stack complète, **keyless** :
 *  - backend FastAPI sur sqlite fichier (seedé), CORS ouvert au preview front ;
 *  - frontend buildé + servi par `vite preview`, pointant sur l'API locale.
 *
 * Chromium est pré-installé dans l'environnement (PLAYWRIGHT_BROWSERS_PATH).
 */
const API = "http://localhost:8000";
const APP = "http://localhost:4173";
const DB = "sqlite+aiosqlite:///./e2e.db";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: APP,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // En CI on installe le navigateur via `npx playwright install chromium`.
        // En local, PW_EXECUTABLE peut pointer un Chromium pré-installé.
        launchOptions: process.env.PW_EXECUTABLE
          ? { executablePath: process.env.PW_EXECUTABLE }
          : {},
      },
    },
  ],
  webServer: [
    {
      // Seed (sqlite fichier partagé) puis API. CORS ouvert au preview front.
      command:
        "rm -f e2e.db && python -m app.db.create_all && python -m app.db.seed && " +
        "uvicorn app.main:app --host 0.0.0.0 --port 8000",
      cwd: "../backend",
      url: `${API}/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: DB,
        ENV: "local",
        // pydantic-settings parse les listes en JSON depuis l'env.
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
      reuseExistingServer: !process.env.CI,
      env: { VITE_API_BASE_URL: `${API}/api/v1` },
    },
  ],
});
