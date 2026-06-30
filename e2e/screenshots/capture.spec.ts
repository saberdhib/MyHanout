import { expect, test } from "@playwright/test";

// Capture des écrans de l'app (preview 4173) et de la vitrine (preview 4321).
// Les PNG vont dans website/public/shots/ (réutilisés par le README et le site).

const SHOTS = "../website/public/shots";

const APP_PAGES: { path: string; name: string; waitFor?: string }[] = [
  { path: "/", name: "dashboard", waitFor: "text=Tableau de bord" },
  { path: "/recommendations", name: "recommendations", waitFor: "text=Recommandations" },
  { path: "/data-ops", name: "data-ops", waitFor: "text=Data Ops" },
  { path: "/alerts", name: "alerts", waitFor: "text=Alertes" },
  { path: "/catalog", name: "catalog", waitFor: "text=Catalogue produits" },
  { path: "/connectors", name: "connectors", waitFor: "text=Connecteurs" },
  { path: "/finance", name: "finance" },
  { path: "/invoices", name: "invoices" },
  { path: "/promos", name: "promos" },
  { path: "/forecasts", name: "forecasts" }, // en dernier (preview parfois lent)
];

test("capture app", async ({ page }) => {
  // Première visite : laisse l'auto-login + le premier chargement se faire.
  await page.goto("/");
  await page.waitForTimeout(3500);
  for (const p of APP_PAGES) {
    try {
      await page.goto(p.path, { waitUntil: "commit", timeout: 15000 });
      if (p.waitFor) {
        await page.locator(p.waitFor).first().waitFor({ state: "visible" }).catch(() => {});
      }
      await page.waitForTimeout(1800); // laisse les données (polling/SSE) arriver
      await page.screenshot({ path: `${SHOTS}/${p.name}.png`, timeout: 20000, animations: "disabled" });
    } catch (e) {
      console.log(`screenshot skip ${p.name}: ${e}`); // une page KO ne casse pas le reste
    }
  }
  expect(true).toBe(true);
});

test("capture site", async ({ page }) => {
  await page.goto("http://localhost:4321/");
  await page.waitForTimeout(2000);
  // Pleine page pour la vitrine (au-dessus + dessous de la ligne de flottaison).
  await page.screenshot({ path: `${SHOTS}/site-home.png`, fullPage: true });
  // Aperçu « above the fold » pour le README.
  await page.screenshot({ path: `${SHOTS}/site-hero.png` });
});
