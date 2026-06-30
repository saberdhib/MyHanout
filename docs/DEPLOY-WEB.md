# Mettre la vitrine en ligne (le plus rapide / pro / gratuit)

La vitrine (`website/`, Astro **statique**) se publie sur un hébergeur de sites
statiques : HTTPS automatique, déploiement à chaque `git push`, gratuit.

## ✅ Recommandé : Cloudflare Pages

1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git** → choisir le repo `MyHanout`.
2. Réglages de build :
   - **Production branch** : `main`
   - **Root directory** : `website`
   - **Build command** : `npm run build`
   - **Build output directory** : `dist`
   - **Environment variable** : `PUBLIC_APP_URL = https://app.myhanout.ai`
     (l'URL où sera servi le dashboard ; le bouton « Lancer l'app » pointe dessus)
3. **Save and Deploy**. À chaque push sur `main`, le site se reconstruit.
4. **Domaine** : onglet *Custom domains* → ajouter `myhanout.ai` (Cloudflare gère
   le DNS + le certificat automatiquement).

> Pourquoi Cloudflare Pages : gratuit, CDN mondial, HTTPS auto, **pas de souci de
> base path** (contrairement à GitHub Pages servi sous `/repo/`), zéro fichier de
> config à committer, zéro secret.

## Fallback : Netlify (zero-config)

Le fichier [`website/netlify.toml`](../website/netlify.toml) est déjà fourni :
*New site from Git* → choisir le repo → Netlify lit `netlify.toml` (base `website`,
build `npm run build`, publish `dist`). Adapter `PUBLIC_APP_URL` si besoin.

## Vérifier le build en local

```bash
cd website && npm install && npm run build   # génère website/dist/
npm run preview                              # sert le rendu en local
```

## Et le dashboard (`frontend/`) + l'API ?

La vitrine est statique ; le **dashboard** a besoin du backend (API + Postgres +
Redis). Deux options (cf. [`DEPLOY.md`](DEPLOY.md)) :

- **VPS tout-en-un** : `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
  (frontend buildé + nginx + migrations auto + ml-service).
- **Séparé** : frontend statique (même hébergeur que la vitrine, root `frontend`,
  build `npm run build`, output `dist`, variable `VITE_API_BASE_URL=https://api.ton-domaine`)
  + backend sur Render/Railway/Fly.io + Postgres managé.

Sous-domaines conseillés : `myhanout.ai` (vitrine), `app.myhanout.ai` (dashboard),
`api.myhanout.ai` (API).
