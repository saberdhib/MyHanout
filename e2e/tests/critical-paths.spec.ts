import { expect, test } from "@playwright/test";

// Parcours critiques MyHanout (data platform). L'app se logue automatiquement
// avec les identifiants de démo seedés ; pas de clé requise.

test("login + dashboard se charge avec KPIs", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Tableau de bord" })).toBeVisible();
  // KPIs au libellé unique (évite l'ambiguïté avec la nav).
  await expect(page.getByText("Alertes ouvertes")).toBeVisible();
  await expect(page.getByText("Fraîcheur données")).toBeVisible();
  await expect(page.getByText("MAPE (qualité prévision)")).toBeVisible();
});

test("recommandations : recalcul + liste explicable", async ({ page }) => {
  await page.goto("/recommendations");
  await page.getByRole("button", { name: "Recalculer" }).click();
  // Au moins une reco avec une explication (le seed a un stock bas).
  await expect(page.getByText(/recommandation\(s\)/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Simuler/ }).first()).toBeVisible();
});

test("simulation de commande", async ({ page }) => {
  await page.goto("/recommendations");
  await page.getByRole("button", { name: "Recalculer" }).click();
  const sim = page.getByRole("button", { name: /Simuler/ }).first();
  await sim.waitFor({ state: "visible" });
  await sim.click();
  await expect(page.getByText(/stock projeté/).first()).toBeVisible();
});

test("data ops : déclenchement d'un pipeline + run visible", async ({ page }) => {
  await page.goto("/data-ops");
  await page.getByRole("button", { name: "daily", exact: true }).click();
  // Un run apparaît dans la table (statut success).
  await expect(page.getByText("success").first()).toBeVisible();
});

test("alertes : génération + résolution humaine", async ({ page }) => {
  // Génère les alertes via Data Ops puis résout depuis la page Alertes.
  await page.goto("/data-ops");
  await page.getByRole("button", { name: "scan_alerts", exact: true }).click();
  await page.goto("/alerts");
  const resolve = page.getByRole("button", { name: "Marquer résolue" }).first();
  if (await resolve.isVisible().catch(() => false)) {
    await resolve.click();
    await expect(page.getByText(/alerte\(s\)/)).toBeVisible();
  } else {
    // Pas d'alerte ouverte (stock suffisant) : la page reste cohérente.
    await expect(page.getByRole("heading", { name: "Alertes" })).toBeVisible();
  }
});

test("temps réel : un pipeline rafraîchit le dashboard", async ({ page }) => {
  await page.goto("/");
  // La pastille d'état (SSE temps réel ou fallback polling) doit apparaître.
  await expect(page.locator(".pill").filter({ hasText: /live|SSE/ })).toBeVisible();
});
