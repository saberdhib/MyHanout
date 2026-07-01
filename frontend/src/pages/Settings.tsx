import { useState } from "react";
import { Card } from "../components/Card";
import { getLang, setLang, t, type Lang } from "../i18n";
import { restartTour } from "../components/TourGuide";

/** Réglages : thème clair/sombre + langue FR/EN + relance du tour. Persisté localement. */
export default function Settings() {
  const [theme, setThemeState] = useState<"light" | "dark">(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );
  const lang = getLang();

  function applyTheme(next: "light" | "dark") {
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem("theme", next);
    setThemeState(next);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t("Réglages")}</h1>
        <p className="text-sm text-night/50 dark:text-surface/50">
          {t("Vos préférences sont enregistrées sur cet appareil.")}
        </p>
      </div>

      <Card title={t("Thème")}>
        <div className="flex gap-2">
          <Choice active={theme === "light"} onClick={() => applyTheme("light")}>
            ☀️ {t("Clair")}
          </Choice>
          <Choice active={theme === "dark"} onClick={() => applyTheme("dark")}>
            🌙 {t("Sombre")}
          </Choice>
        </div>
      </Card>

      <Card title={t("Langue")}>
        <div className="flex gap-2">
          <Choice active={lang === "fr"} onClick={() => lang !== "fr" && setLang("fr" as Lang)}>
            🇫🇷 {t("Français")}
          </Choice>
          <Choice active={lang === "en"} onClick={() => lang !== "en" && setLang("en" as Lang)}>
            🇬🇧 {t("Anglais")}
          </Choice>
        </div>
      </Card>

      <Card title={t("Préférences")}>
        <button
          onClick={restartTour}
          className="rounded-card border border-night/15 px-3 py-2 text-sm dark:border-white/15"
        >
          🔁 {t("Revoir le tour de bienvenue")}
        </button>
      </Card>
    </div>
  );
}

function Choice({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-card px-4 py-2 text-sm font-semibold transition-colors ${
        active
          ? "bg-brand text-white"
          : "border border-night/15 hover:bg-brand/5 dark:border-white/15"
      }`}
    >
      {children}
    </button>
  );
}
