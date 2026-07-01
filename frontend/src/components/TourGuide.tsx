import { useState } from "react";
import { t } from "../i18n";

/**
 * Tour de bienvenue (première visite) : présente chaque zone de l'app en quelques
 * étapes. Affiché une seule fois (localStorage), relançable depuis Réglages.
 */
const DONE_KEY = "mh_tour_done";

export function restartTour(): void {
  localStorage.removeItem(DONE_KEY);
  window.location.assign("/");
}

type Step = { icon: string; title: string; desc: string; goto?: string };

const STEPS: Step[] = [
  {
    icon: "👋",
    title: "Bienvenue sur MyHanout AI",
    desc: "Votre copilote IA. Il observe vos ventes, stocks et factures, puis vous propose des actions. Vous gardez toujours la main : rien ne part sans votre accord.",
  },
  {
    icon: "☀️",
    title: "Briefing du matin",
    desc: "Chaque jour, vos agents IA consolident l'essentiel : alertes, réassort, démarques, production. Une liste d'actions priorisées, à cocher — envoyable sur WhatsApp.",
    goto: "/briefing",
  },
  {
    icon: "🛒",
    title: "Recommandations & prévisions",
    desc: "Quoi commander, combien, quand — avec l'explication (demande prévue, stock, signaux comme la météo ou un match). Testez « et si je commande X ? ».",
    goto: "/recommendations",
  },
  {
    icon: "🏷️",
    title: "Démarque anti-gaspi",
    desc: "Avant qu'un lot frais parte à la poubelle, l'IA propose la remise qui récupère un maximum de valeur. Vous appliquez ou ignorez.",
    goto: "/markdown",
  },
  {
    icon: "📊",
    title: "Finance & bilan hebdo",
    desc: "Factures lues automatiquement (OCR), marges par produit, trésorerie, et un bilan de la semaine avec 3 actions concrètes.",
    goto: "/report",
  },
  {
    icon: "🔌",
    title: "Connecteurs",
    desc: "Branchez VOS comptes WhatsApp, Slack ou Telegram, votre caisse et vos capteurs. Sans clé, tout fonctionne en mode démo — idéal pour explorer.",
    goto: "/connectors",
  },
  {
    icon: "💬",
    title: "Assistant IA",
    desc: "Une question ? La bulle de chat en bas à droite répond partout dans l'app : « quel est mon stock de tomates ? », « prépare le bilan »…",
  },
];

export default function TourGuide() {
  const [open, setOpen] = useState(() => !localStorage.getItem(DONE_KEY));
  const [step, setStep] = useState(0);

  if (!open) return null;

  function finish(goto?: string) {
    localStorage.setItem(DONE_KEY, "1");
    setOpen(false);
    if (goto) window.location.assign(goto);
  }

  const s = STEPS[step];
  const last = step === STEPS.length - 1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-night/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={t("Bienvenue sur MyHanout AI 👋")}
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-night dark:text-surface">
        <div className="text-4xl">{s.icon}</div>
        <h2 className="mt-3 text-xl font-bold">{s.title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-night/60 dark:text-surface/60">{s.desc}</p>

        {/* Progression */}
        <div className="mt-5 flex items-center gap-1.5">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? "w-6 bg-brand" : "w-1.5 bg-night/15 dark:bg-white/15"
              }`}
            />
          ))}
        </div>

        <div className="mt-5 flex items-center justify-between">
          <button
            onClick={() => finish()}
            className="text-sm text-night/40 hover:underline dark:text-surface/40"
          >
            {t("Passer")}
          </button>
          <button
            onClick={() => (last ? finish() : setStep(step + 1))}
            className="rounded-card bg-brand px-4 py-2 text-sm font-semibold text-white"
          >
            {last ? t("C'est parti !") : t("Suivant")}
          </button>
        </div>
      </div>
    </div>
  );
}
