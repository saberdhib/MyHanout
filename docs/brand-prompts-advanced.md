# Prompts image AVANCÉS — génération automatisée (Codex / gpt-image-1)

> Version « hyper avancée » de `docs/brand-prompts.md`, pensée pour être exécutée par
> un **agent** (Codex + API OpenAI `gpt-image-1`) qui génère chaque asset et le dépose
> **directement au bon chemin du repo**. Les prompts sont en **anglais** (meilleure
> adhérence des modèles d'image) ; les specs (chemin, tailles, post-traitement) sont
> normatives. Le prompt de mission Codex est en fin de fichier.

---

## 🎨 STYLE CORE (à préfixer à CHAQUE prompt)

```
Brand art direction — "MyHanout AI", an AI copilot for neighborhood food retailers.
Aesthetic: premium flat design, generous negative space, soft diffused shadows,
rounded corners (~12px radius), crisp vector-like edges, absolutely no gradients
except a barely perceptible green tile gradient, no photorealistic clutter, no text
unless explicitly requested, no watermarks.
EXACT palette, use ONLY these colors:
- Signature green #12B76A (accents, CTAs, tile fills)
- Deep green #0E7A4A (subtle gradient ends, borders)
- Navy #0F172A (dark backgrounds, primary text shapes)
- Navy-2 #1E293B (cards on dark backgrounds)
- Sand #F1F5F9 (light backgrounds, light cards)
- Amber #F59E0B (ONE small decorative 4-point sparkle max)
- Slate #94A3B8 / Muted #64748B (secondary strokes)
- Teal #14B8A6 / Mint #5EEAD4 (rare accents)
Brand mark (reference image attached when supported): a white storefront with a
scalloped awning, a small amber dot and a navy arched door, inside a green rounded
tile whose bottom-right corner forms a chat-bubble tail. Reproduce it FAITHFULLY,
never redesign it.
Typography if any: Manrope, geometric sans, bold titles.
Mood: "the AI that assists, never the AI that takes over" — calm, trustworthy,
professional; motion and decoration serve readability, never spectacle.
```

**Référence logo** : joindre `frontend/public/logo-icon.png` en image de référence
(édition/variation) quand l'API le permet ; sinon compter sur la description ci-dessus.

---

## Assets à générer

### A1 — Hero vitrine (paysage clair)
- **Fichier** : `website/public/hero.png` · **Génération** : 1536×1024 → **recadrer 1600×640** (bande centrale), PNG < 600 Ko.
```
Wide hero illustration for a premium B2B SaaS landing page, light theme on white
fading to sand #F1F5F9. Center-right: a floating, slightly 3D-tilted flat mockup of
a retail analytics dashboard — sand-colored cards, one green #12B76A area line chart
trending up, small KPI tiles, a donut chart with green/teal/navy segments, blurred
placeholder text bars (no readable words). Left of it: a green chat bubble stack
evoking a WhatsApp conversation (generic, no third-party logo), one bubble containing
a tiny bar chart. One small amber #F59E0B 4-point sparkle floating near the top of
the dashboard. Soft drop shadows, flat premium vector style, lots of negative space
at the left for headline placement.
```

### A2 — Illustration « équipe d'agents IA »
- **Fichier** : `website/public/illustrations/agents.png` · **Génération** : 1024×1024 → **900×900**, fond transparent si possible sinon blanc.
```
Flat premium illustration: the brand storefront tile (white scalloped-awning shop
inside a green #12B76A rounded chat-bubble tile) at the center, orbited by 8 small
round satellite chips connected by thin slate #94A3B8 lines, like a calm constellation.
Each chip is a minimal line icon on a sand #F1F5F9 disc with a thin green ring:
shopping cart, price tag, bar chart, alert bell, bread loaf, thermometer, invoice
sheet, chat bubble. One tiny amber #F59E0B sparkle between two chips. Balanced
radial composition, generous spacing, no text.
```

### A3 — Briefing du matin sur téléphone (portrait)
- **Fichier** : `website/public/illustrations/briefing-phone.png` · **Génération** : 1024×1536 → **800×1200**.
```
Flat premium illustration of a modern smartphone, straight-on, floating with a soft
shadow on a very light sand #F1F5F9 background. On screen: a messaging conversation
(generic green chat app, no third-party branding) showing a "morning briefing" from
an assistant — a sun glyph header bubble, then a checklist bubble with 4 rows, each
row a small colored tag (red alert dot, amber price tag, green cart, navy bread icon)
followed by blurred placeholder text bars (no readable words). The brand storefront
tile appears as the conversation avatar at the top. One amber #F59E0B sparkle beside
the phone. Calm, trustworthy, human-scale.
```

### A4 — Flux de données (schéma décoratif sombre)
- **Fichier** : `website/public/illustrations/data-flow.png` · **Génération** : 1536×1024 → **1600×900**.
```
Dark premium schematic illustration on navy #0F172A. Three vertical zones connected
left-to-right by thin glowing green #12B76A lines with small animated-looking nodes:
LEFT — four small navy-2 #1E293B cards with minimal white line icons (receipt,
cash register, thermometer, cloud). CENTER — the brand storefront tile (white shop
in green rounded chat-bubble tile) inside a subtle concentric ring halo, one amber
#F59E0B sparkle at its top-right. RIGHT — three cards with line icons (phone chat
bubble, dashboard bars, bell). Faint dotted grid in the background, mint #5EEAD4
micro-accents on two nodes. No text anywhere. Feels like calm data flowing through
a trusted engine.
```

### A5 — Verticaux métier (4 cartes carrées)
- **Fichiers** : `website/public/verticals/boucherie.png`, `boulangerie.png`, `primeur.png`, `epicerie.png` · **Génération** : 1024×1024 → **800×800** chacun.
- Prompt commun + variante :
```
Flat premium square illustration on navy #0F172A with a soft green #12B76A rim light
from the left. Centered subject rendered in the brand's flat vector style with sand
#F1F5F9 and green surfaces, navy-2 #1E293B depth planes, thin mint #5EEAD4 accents,
one small amber #F59E0B sparkle. Composition breathes, subject fills ~60% of frame,
no text, no people faces in close-up.
SUBJECT (boucherie): a butcher's marble counter with two elegant flat cuts of meat on
a wooden board, a steel scale, and a small hanging price tag.
SUBJECT (boulangerie): a rustic bread rack with baguettes and round loaves, a paddle,
gentle heat glow suggested by amber-tinted highlights (keep amber minimal).
SUBJECT (primeur): wooden crates of stylized fruits and vegetables (tomatoes, greens,
oranges) stacked on a market stand with a striped awning edge.
SUBJECT (epicerie): tidy grocery shelves with jars, cans, bottles and paper bags,
a small step ladder leaning on the side.
```

### A6 — Open Graph (fond, texte ajouté ensuite)
- **Fichier** : `website/public/og-bg.png` · **Génération** : 1536×1024 → **1200×630** (recadrage central).
- ⚠️ Générer **sans texte** ; le wordmark/tagline sera composé par-dessus (Manrope) via Pillow avec `website/public/logo-wordmark.png`.
```
Social share background, deep navy #0F172A with a very diffuse green #12B76A glow
rising from the bottom-right corner and a faint dotted grid. Bottom-left quadrant:
the brand storefront tile at ~180px scale with a soft shadow. One small amber
#F59E0B sparkle top-right. Two thin concentric teal #14B8A6 arcs barely visible
behind the tile. Large clean empty area on the left 60% for text overlay. No text.
```

### A7 — Bannière GitHub / présentation (refresh)
- **Fichier** : `docs/assets/banner.png` · **Génération** : 1536×1024 → **1280×512** (bande centrale).
```
Wide banner, split composition. Left 45%: navy #0F172A panel with the brand
storefront tile and a soft green glow, one amber sparkle, faint dotted grid.
Right 55%: light sand #F1F5F9 panel with a flat dashboard mockup (green area chart,
KPI tiles, donut chart, blurred text bars) and a floating phone showing a green chat
conversation, both with soft shadows. A thin green #12B76A seam separates the two
panels. Premium, calm, no readable text.
```

### A8 — Pictogrammes fonctions (8 icônes individuelles)
- **Fichiers** : `website/public/picto/{invoice,reorder,forecast,alert,chat,markdown,production,haccp}.png` · **Génération** : 1024×1024 chacun → **512×512**, **fond transparent**.
```
Single minimal line icon, consistent 24px-grid style scaled up: stroke-only, uniform
6px stroke at 512px, rounded caps and joins, color green #12B76A on fully transparent
background, centered with 15% margins, no fill except one optional tiny amber
#F59E0B dot accent. SUBJECT: {invoice: a receipt sheet with a scan line} |
{reorder: a shopping basket with a circular refresh arrow} | {forecast: a rising
line chart with a small sun} | {alert: a bell with one motion arc} | {chat: a
rounded chat bubble with three dots} | {markdown: a price tag with a percent sign} |
{production: a round loaf with a chef hat outline} | {haccp: a shield with a
checkmark and a tiny thermometer}.
```

### A9 — Empty-states de l'app (3 douceurs)
- **Fichiers** : `frontend/public/empty/{calm,search,success}.png` · **Génération** : 1024×1024 → **600×600**, fond transparent si possible.
```
Tiny friendly spot illustration, flat premium style, mostly line-art with two flat
fills max (green #12B76A + sand #F1F5F9), transparent background, no text.
SUBJECT (calm): the brand storefront tile asleep under a crescent moon and one amber
sparkle — "nothing urgent today". SUBJECT (search): a magnifying glass over an empty
open cardboard box. SUBJECT (success): a clipboard with all boxes checked and one
amber sparkle.
```

---

## Post-traitement obligatoire (Pillow)
1. Redimensionner/recadrer aux **tailles finales** ci-dessus (LANCZOS, recadrage centré).
2. PNG optimisé (`optimize=True`) ; viser < 600 Ko par fichier (hero/banner < 900 Ko).
3. `og.png` final = `og-bg.png` + wordmark `website/public/logo-wordmark.png` collé à
   gauche (hauteur ~140px, marge 80px) — pas de texte généré par le modèle.
4. Ne **jamais** écraser `logo-icon.png`, `logo-wordmark*.png`, `favicon*`, `shots/`.

## Câblage après génération (fait par l'agent)
- `website/src/pages/index.astro` : rien à changer si les chemins ci-dessus sont respectés
  (hero.png remplacé sur place) ; les nouveaux dossiers `illustrations/`, `verticals/`,
  `picto/`, `empty/` sont des assets disponibles, câblage UI optionnel hors périmètre.

---

## 🤖 Prompt de mission Codex (copier-coller tel quel)

```
Tu travailles dans le repo MyHanout (monorepo backend FastAPI + frontend React +
website Astro). Ta mission : générer les assets de marque décrits dans
docs/brand-prompts-advanced.md et les déposer aux chemins EXACTS indiqués.

Règles :
1. Lis docs/brand-prompts-advanced.md en entier avant d'agir. Le "STYLE CORE" doit
   être préfixé à chaque prompt d'asset. frontend/public/logo-icon.png est la
   référence fidèle du logo (utilise-la en image de référence si l'API le permet).
2. Utilise l'API OpenAI Images (model "gpt-image-1") via la variable d'environnement
   OPENAI_API_KEY. Si la clé est absente, STOP : n'invente pas d'images, ne commite
   rien, explique ce qui manque.
3. Écris un script Python jetable (scripts/generate_brand_assets.py) qui : génère
   chaque asset (tailles de génération indiquées, background transparent quand
   spécifié, quality high), applique le post-traitement Pillow (recadrage centré,
   tailles finales, optimize=True, composition de og.png = og-bg + wordmark), et
   sauvegarde aux chemins cibles en créant les dossiers manquants.
4. Interdits : écraser logo-icon.png, logo-wordmark*.png, favicon*, website/public/shots/,
   toucher au code applicatif, ajouter des dépendances au package.json / pyproject
   (openai + pillow en pip install local suffisent).
5. Vérifie chaque fichier produit : dimensions exactes, poids < 600 Ko (hero/banner
   < 900 Ko), transparence effective pour picto/ et empty/.
6. Commit sur une branche feat/brand-assets-generated avec un message clair listant
   les fichiers, puis push. N'ouvre pas de PR, ne merge pas.
7. Rends-compte : liste des assets générés (chemin + dimensions + poids), ceux qui
   ont échoué et pourquoi, et le coût API approximatif.
```
