# MyHanout AI — Site vitrine

Site marketing public (landing, tarifs, confiance/RGPD, contact), **séparé du dashboard**
(`frontend/` = l'app authentifiée). Construit en **Astro + Tailwind**, statique (SSG),
SEO natif, réutilise l'identité de marque (vert `#12B76A`, Manrope).

## Lancer

```bash
cd website
npm install
npm run dev        # http://localhost:4321
npm run build      # génère dist/ (statique)
npm run preview    # prévisualise le build
```

## Configuration

- `PUBLIC_APP_URL` : URL du dashboard (boutons « Connexion » / « Essayer »).
  Défaut `http://localhost:5173`. En prod : `PUBLIC_APP_URL=https://app.myhanout.ai`.

## Structure

```
src/
  consts.ts            métadonnées site + navigation + URL de l'app
  layouts/Base.astro   <head> SEO/OG, nav, footer, reveal au scroll
  components/          Logo, Nav, Footer, BrowserFrame
  pages/               index, pricing, confiance, contact
  styles/global.css    design system (btn, card, eyebrow, reveal)
public/shots/          captures réelles du dashboard
```

## Déploiement

Sortie 100 % statique (`dist/`) : déployable sur Vercel / Netlify / Cloudflare Pages,
ou servi par nginx. Build : `npm run build`. Aucune dépendance runtime.
