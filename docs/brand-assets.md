# Assets de marque — checklist de production

Charte : Manrope (titres bold, corps regular), sobre/premium B2B, coins ~12px,
ombres douces, pas d'emoji sauf le **✦ ambre** décoratif.

**Palette (référence)** — déjà câblée dans `frontend/src/theme/tokens.js` :

| Rôle | Hex |
|------|-----|
| Vert signature (CTA/accent) | `#12B76A` |
| Vert foncé (dégradés/bordures) | `#0E7A4A` |
| Navy (fond sombre / texte clair) | `#0F172A` |
| Navy 2 (cartes sombres) | `#1E293B` |
| Sable (cartes claires) | `#F1F5F9` |
| Ambre (✦, 1 accent/écran) | `#F59E0B` |
| Slate (texte secondaire/sombre) | `#94A3B8` |
| Muted (texte secondaire/clair) | `#64748B` |
| Teal / Mint (variations) | `#14B8A6` / `#5EEAD4` |

> Dès que les fichiers sont déposés aux chemins ci-dessous (puis `git add` + push),
> je remplace les placeholders et je vérifie le rendu (favicon, PWA, header, OG).

---

## 1. Logo système (le minimum vital)

| Fichier (déposer ici) | Format | Dimensions | Notes |
|---|---|---|---|
| `frontend/public/favicon.svg` *(remplace le placeholder)* | **SVG** | carré | L'icône seule (échoppe). Fond transparent. |
| `frontend/src/assets/logo-icon.svg` | **SVG** | carré (viewBox 0 0 48 48) | Marque seule, couleurs de marque. Sidebar repliée + header. |
| `frontend/src/assets/logo-wordmark.svg` | **SVG** | ~ 160×32 | Marque + texte « MyHanout AI ». **Astuce** : mettre le **texte en `currentColor`** → il s'adapte automatiquement (navy sur clair, blanc sur sombre), un seul fichier. |
| `website/public/favicon.svg` *(remplace)* | **SVG** | carré | Idem icône. |
| `website/src/assets/logo-wordmark.svg` | **SVG** | ~ 160×32 | Header vitrine (même fichier que l'app, copié). |

Si tu n'as pas de SVG : fournis un **PNG transparent 1024×1024** de l'icône
(`logo-icon-1024.png`) — je génère les dérivés moi-même.

## 2. Icônes PWA / favicons (raster, fond plein)

| Fichier | Format | Dimensions | Notes |
|---|---|---|---|
| `frontend/public/icons/icon-192.png` *(remplace)* | PNG | 192×192 | Tuile **pleine** (fond vert `#12B76A` jusqu'aux bords, échoppe blanche). Sert aussi d'`apple-touch-icon`. |
| `frontend/public/icons/icon-512.png` *(remplace)* | PNG | 512×512 | Idem, pleine résolution. |
| `frontend/public/icons/icon-512-maskable.png` *(remplace)* | PNG | 512×512 | **Maskable** : logo centré dans la **zone sûre ≈ 80 %** (cercle/au carré masqué par Android), fond vert jusqu'aux bords. |
| `frontend/public/apple-touch-icon.png` *(optionnel, recommandé)* | PNG | 180×180 | iOS net ; sinon iOS réutilise le 192. |

> `background_color` PWA = `#0F172A`, `theme_color` = `#12B76A` (déjà réglés).

## 3. Image de partage social (Open Graph)

| Fichier | Format | Dimensions | Notes |
|---|---|---|---|
| `website/public/og.png` *(remplace `og.svg`)* | **PNG** | **1200×630** | Carte LinkedIn/Twitter. Fond **navy `#0F172A`**, wordmark blanc + tagline « Votre copilote IA pour des commerces plus performants », ✦ ambre. PNG car certains réseaux ne rendent pas le SVG. *(Je mets à jour la balise `og:image` vers `og.png`.)* |

## 4. Visuel Hero vitrine (optionnel mais fort)

| Fichier | Format | Dimensions | Notes |
|---|---|---|---|
| `website/public/hero.png` (ou `.svg`) | PNG/SVG | ~ 1600×1200 (2x) | Mockup du dashboard (dans un cadre device) ou illustration. Fond transparent (posé sur section claire ou navy). Sobre, beaucoup d'air. |
| `website/public/hero-mobile.png` *(optionnel)* | PNG | ~ 800×1000 | Variante portrait pour petits écrans. |

> À défaut de hero dédié, j'utilise une **capture du dashboard** (déjà dans
> `website/public/shots/`) dans un cadre — dis-moi si tu préfères ça.

---

## Récap « strict minimum » pour un rendu pro tout de suite
1. `favicon.svg` (app + site) — l'icône
2. `logo-wordmark.svg` (texte en `currentColor`)
3. `icons/icon-192.png`, `icon-512.png`, `icon-512-maskable.png`
4. `website/public/og.png` (1200×630)

Le reste (apple-touch-icon, hero) est bonus. **Ou** donne-moi juste un master
`logo-icon-1024.png` + le `logo-wordmark.svg`, et je génère tous les dérivés.
