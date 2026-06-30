# Prompts ChatGPT (image) — assets de marque MyHanout AI

Mode d'emploi : dans ChatGPT (génération d'image), **joins ton logo** + colle le
**préambule** ci-dessous, puis le prompt de l'asset voulu. Tailles natives utiles :
`1024×1024` (carré), `1536×1024` (paysage 3:2), `1024×1536` (portrait).

> ⚠️ Les modèles d'image **se trompent souvent sur le texte**. Pour tout asset avec
> du texte (OG, wordmark), soit tu vérifies l'orthographe, soit tu génères le **fond
> sans texte** et tu ajoutes le texte dans Canva/Figma (police **Manrope**).

---

## 🎨 Préambule (à coller en tête de CHAQUE prompt)

```
Direction artistique — MyHanout AI (copilote IA des commerces de proximité).
Style : sobre, premium, B2B, beaucoup d'air, plat (flat), ombres douces, coins
arrondis ~12px, AUCUN dégradé criard, AUCUN emoji sauf une étincelle ✦ ambre
décorative et discrète. Typo des textes : Manrope (sans-serif géométrique), titres bold.
Palette EXACTE (n'utilise que ces couleurs) :
- Vert signature #12B76A (accent/CTA)
- Vert foncé #0E7A4A (dégradés très subtils, bordures)
- Navy #0F172A (fonds sombres / texte sur clair)
- Navy 2 #1E293B (cartes sur fond sombre)
- Sable #F1F5F9 (cartes / fonds clairs)
- Ambre #F59E0B (l'étincelle ✦, 1 accent max)
- Slate #94A3B8 (texte secondaire sombre) / Muted #64748B (texte secondaire clair)
- Teal #14B8A6 / Mint #5EEAD4 (variations ponctuelles)
Logo en pièce jointe = référence à respecter À L'IDENTIQUE (échoppe blanche : auvent
festonné + petit personnage, dans une bulle de chat verte). Ne le redessine pas
librement, reprends-le fidèlement.
```

---

## 1. Icône d'app — master carré (PNG 1024×1024)
> Sert à générer favicon + icônes PWA.
```
Crée une ICÔNE D'APPLICATION carrée 1024×1024, style iOS (coins arrondis ~22%).
Tuile remplie jusqu'aux bords en vert #12B76A (très léger dégradé vers #0E7A4A,
quasi imperceptible). Au centre, mon logo (échoppe blanche dans la bulle de chat),
blanc pur, marges égales, bien centré. AUCUN texte. Rendu net, plat, premium,
légère ombre portée interne. Fond opaque (pas de transparence).
```

## 2. Icône PWA "maskable" (PNG 1024×1024, zone de sécurité)
```
Même icône que précédemment, mais version "maskable" pour Android : le logo
(échoppe) doit tenir dans la ZONE DE SÉCURITÉ CENTRALE (~66% du carré, cercle de
découpe), avec une marge verte #12B76A généreuse tout autour qui remplit le carré
jusqu'aux bords. Aucun élément important près des bords/coins. Pas de texte.
```

## 3. Favicon (PNG 512×512, lisible en tout petit)
```
Version ULTRA simplifiée de mon logo pour un favicon lisible à 16px : l'échoppe
blanche stylisée sur tuile vert #12B76A, coins arrondis. Supprime les détails fins,
garde la silhouette reconnaissable (auvent + bulle). Pas de texte, fond opaque.
```

## 4. Image de partage social — Open Graph (PNG, 1536×1024 → recadrer en 1200×630)
> LinkedIn / Twitter. Si le texte sort mal, génère SANS texte et ajoute-le dans Canva.
```
Visuel de partage social, fond Navy #0F172A uni avec un halo vert #12B76A très diffus
en bas à droite. À gauche : mon logo (icône) + le wordmark « MyHanout AI » (le mot
« AI » en vert #12B76A) avec une petite étincelle ✦ ambre #F59E0B en exposant.
En dessous, la tagline en Slate #94A3B8 : « Votre copilote IA pour des commerces plus
performants ». Beaucoup d'air, composition épurée, premium. Police type Manrope bold.
```

## 5. Visuel Hero (PNG 1536×1024, paysage)
> Pour la grande image d'accueil de la vitrine (au-dessus de la ligne de flottaison).
```
Illustration hero épurée et premium pour un SaaS B2B : une maquette stylisée de
tableau de bord (cartes claires Sable #F1F5F9, petites courbes/indicateurs en vert
#12B76A et teal #14B8A6, badges) flottant légèrement, avec une bulle de messagerie
verte évoquant WhatsApp à côté (sans logo tiers). Fond clair (blanc → Sable),
ombres douces, coins arrondis ~12px, beaucoup d'espace négatif, une seule étincelle
✦ ambre #F59E0B. Pas de texte lisible (placeholders flous). Style flat, net, élégant.
```

## 6. (Bonus) Pictogrammes de fonctions (PNG 1024×1024, jeu cohérent)
> Si tu veux remplacer les icônes SVG par un set illustré.
```
Crée un jeu de 6 pictogrammes line-art cohérents (même épaisseur de trait, coins
arrondis), couleur vert #12B76A sur fond transparent, style minimal premium :
1) facture/scan, 2) panier/réassort, 3) courbe de prévision, 4) cloche d'alerte,
5) bulle de chat, 6) maillons/dépendances. Grille uniforme, marges égales, pas de texte.
```

---

## Où déposer les fichiers générés (cf. `docs/brand-assets.md`)
- Icône → `frontend/public/icons/icon-192.png`, `icon-512.png`, `icon-512-maskable.png`
- Favicon → `frontend/public/favicon.svg` (ou .png) + `website/public/favicon.svg`
- OG → `website/public/og.png`
- Hero → `website/public/hero.png`
- Master logo → `frontend/public/logo-icon.png` + `website/public/logo-icon.png`

Dépose, push sur `main`, dis-moi « c'est bon » → je câble tout (favicons, PWA, header
app + vitrine, OG) et on déploie.
