# 🔒 Checklist « passage en public » — MyHanout AI

> Fichier **interne**, à actionner le jour où tu rends le repo public.
> Ordre : **1) exporte une archive de sauvegarde** (pour garder ces fichiers chez toi)
> → **2) retire-les du repo** → **3) vérifie l'historique git** (voir ⚠️ tout en bas).
>
> ⚠️ Ce fichier (`PRE-PUBLIC-CLEANUP.md`) fait **lui-même partie** de ce qui doit sortir.

---

## 1. À RETIRER absolument (interne / stratégie / production)

Ces fichiers révèlent ton « comment c'est fait » business ou tes outils de prod — aucune
raison qu'ils soient publics.

| Chemin | Pourquoi on l'enlève |
|---|---|
| `brand-incoming/` (dossier complet) | tes fichiers sources de logos/visuels bruts |
| `docs/brand-prompts.md` | prompts ChatGPT de génération d'assets (savoir-faire interne) |
| `docs/brand-assets.md` | checklist interne de production des visuels |
| `docs/delivery/` (**dossier complet**) | livrables conseil : discovery business, **stratégie IA**, archi solution/data, ADRs |
| `docs/delivery/privacy-pricing.md` | **pricing & confidentialité** — sensible (inclus dans le dossier ci-dessus) |
| `docs/roadmap.md` | feuille de route interne (priorités, à venir) |
| `PRE-PUBLIC-CLEANUP.md` | ce fichier-ci |

## 2. À DÉCIDER (ton appel — relire avant de trancher)

Pas bloquant, mais à relire d'un œil « est-ce que je veux que le monde voie ça ? ».

| Chemin | Remarque |
|---|---|
| `CLAUDE.md` | guide de dev + **« pièges réels »** internes. Beaucoup de repos le gardent (signe de sérieux), mais il dévoile ta cuisine. À toi de voir. |
| `docs/governance.md` | gouvernance interne — souvent OK en public, relis le contenu. |
| `docs/DEPLOY.md`, `docs/DEPLOY-WEB.md` | notes de déploiement : vérifie qu'aucun nom d'hôte / chemin infra réel ne traîne. |
| `docs/DEMO.md` | scénario de démo — OK si données fictives uniquement. |
| `website/public/shots/`, `e2e/screenshots/` | captures d'écran : OK tant qu'elles ne montrent que la **donnée démo fictive** (org « demo »). |

## 3. À GARDER (c'est le produit — fait pour être vu)

`README.md`, `LICENSE`, `SECURITY.md`, **tout le code** (`backend/`, `frontend/`, `website/`,
`ml-service/`, `analytics/`), et les docs techniques :
`architecture.md`, `api-design.md`, `data-model.md`, `multitenancy.md`,
`configuration.md`, `data-engineering.md`, `ai-models.md`, `retail-platform.md`.

> Rappel : les secrets ne sont **jamais** dans le repo (que des `.env.example` à placeholders).
> Vérifie quand même : `git ls-files | grep -iE '\.env$|secret|credential'` doit ne sortir
> que des `.example`.

---

## 4. Commandes prêtes à l'emploi

### Étape 1 — Exporter une archive de sauvegarde (À FAIRE EN PREMIER)

```bash
# Crée une archive horodatée de TOUT ce qu'on va retirer, hors du repo (~/)
tar -czf ~/myhanout-internal-backup.tgz \
  brand-incoming \
  docs/brand-prompts.md \
  docs/brand-assets.md \
  docs/delivery \
  docs/roadmap.md \
  PRE-PUBLIC-CLEANUP.md 2>/dev/null
echo "Sauvegarde -> ~/myhanout-internal-backup.tgz"
```

### Étape 2 — Retirer du repo (après avoir vérifié l'archive)

```bash
git rm -r --cached --ignore-unmatch \
  brand-incoming \
  docs/brand-prompts.md \
  docs/brand-assets.md \
  docs/delivery \
  docs/roadmap.md \
  PRE-PUBLIC-CLEANUP.md
# supprime aussi du disque :
rm -rf brand-incoming docs/brand-prompts.md docs/brand-assets.md \
       docs/delivery docs/roadmap.md PRE-PUBLIC-CLEANUP.md
git commit -m "chore: retire les documents internes avant passage en public"
```

> Si tu décides aussi de sortir des fichiers de la section 2, ajoute-les aux deux
> listes ci-dessus (archive **et** `git rm`).

---

## ⚠️ Point CRITIQUE : l'historique git

`git rm` enlève les fichiers du **dernier commit**, mais ils restent **consultables dans
l'historique** (`git log`, anciens commits). Pour un repo vraiment confidentiel, ça ne suffit pas.

**Deux options selon ton niveau d'exigence :**

1. **Le plus simple et le plus sûr** — publier un **repo neuf** à partir d'un snapshot propre
   (sans historique). Sur une copie nettoyée :
   ```bash
   rm -rf .git && git init && git add -A
   git commit -m "Initial public release"
   # puis push vers le NOUVEAU repo public
   ```
   Tu gardes ton repo privé actuel (avec tout l'historique) de ton côté.

2. **Réécrire l'historique** du repo existant avec `git filter-repo`
   (`pip install git-filter-repo`) — plus technique, irréversible, à faire sur un clone :
   ```bash
   git filter-repo --invert-paths \
     --path docs/brand-prompts.md --path docs/brand-assets.md \
     --path docs/roadmap.md --path PRE-PUBLIC-CLEANUP.md \
     --path-glob 'docs/delivery/*' --path-glob 'brand-incoming/*'
   ```

👉 **Recommandation : option 1** (repo public neuf). Plus net, zéro risque de fuite via
l'historique, et tu conserves ton repo privé intact comme base de travail.
