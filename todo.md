# YotoShare - Migration Plan

## Contexte
Séparation de l'ancien projet (galerie communautaire + partage) en deux projets distincts.
Ce repo = partie partage uniquement. Nouveau domaine : **yotoshare.com**
Ancien domaine : `lib.yoto.webuso.fr`

---

## 1. Git & Branches

- [x] Renommer la branche `master` en `legacy` (conserver l'historique de l'ancien projet)
- [x] Mettre à jour `origin/HEAD` pour pointer vers `main`
- [x] Supprimer la branche `master` sur le remote après renommage
- [x] Mettre à jour la branche par défaut sur GitHub → `main`

## 2. Domaine & URLs → yotoshare.com

- [x] Mettre à jour `BASE_URL` dans `.env.example` → `https://yotoshare.com`
- [x] Mettre à jour `CORS_ORIGINS` dans `.env.example` pour inclure `https://yotoshare.com`
- [ ] Mettre à jour `.env` local au déploiement (BASE_URL, YOTO_REDIRECT_URI, CORS_ORIGINS)
- [x] SSL/TLS géré par Traefik + Let's Encrypt (certresolver configuré dans les labels)

## 3. Migration des anciens liens (lib.yoto.webuso.fr → yotoshare.com)

- [x] Configurer redirection 301 via Traefik labels (redirectregex middleware sur le stack `yotoshare`)
- [ ] **Au déploiement** : pointer le DNS de `lib.yoto.webuso.fr` vers le même serveur que `yotoshare.com`
- [ ] Conserver le même `SECRET_KEY` pour que les tokens existants restent valides
- [ ] Stopper le stack `yoto-library` une fois la migration validée

## 4. Discord Bot

- [x] Les URLs du bot sont dynamiques (basées sur `BASE_URL`) → aucun changement de code nécessaire
- [ ] Tester la publication post-migration (share links, cover URLs, download buttons)

## 5. Komodo - Stacks

### Stack `yotoshare` (prod) - CONFIG PRÊTE, NON DÉPLOYÉE
- [x] Compose mis à jour : 3 services (backend, frontend, nginx) au lieu d'1
- [x] Images : `ghcr.io/bubu31/yoto-library-backend/frontend/nginx:latest`
- [x] Traefik : routage `yotoshare.com` (HTTPS + redirect HTTP→HTTPS)
- [x] Traefik : redirect 301 `lib.yoto.webuso.fr` → `yotoshare.com` (via redirectregex)
- [x] Environnement : BASE_URL, Discord, NFS, secrets — tout configuré
- [ ] **Déployer** quand prêt

### Stack `yoto-library-staging` → `staging.yotoshare.com` - CONFIG PRÊTE, NON DÉPLOYÉE
- [x] Compose mis à jour : containers renommés `yotoshare-staging-*`
- [x] Domaine : `staging.yotoshare.com` (avant : `staging.yotolib.com`)
- [x] Traefik : HTTPS + redirect HTTP→HTTPS (manquait avant)
- [ ] **Déployer** quand prêt

### Stack `yoto-library` (ancienne prod sur lib.yoto.webuso.fr)
- [ ] À stopper après migration validée (la redirection Traefik est sur le stack `yotoshare`)

## 6. Vérifications post-migration

- [ ] Tester les pages de partage (`/share/{token}`) - OG meta, preview Discord
- [ ] Tester le téléchargement via tokens existants
- [ ] Tester la publication Discord (nouveau lien yotoshare.com)
- [ ] Tester les packs (`/pack/{token}`)
- [ ] Vérifier les redirections 301 depuis `lib.yoto.webuso.fr`
- [ ] Vérifier que les anciens liens Discord fonctionnent encore (via redirect)

---

## Notes

- Aucune référence à l'ancien domaine dans le code source — tout passe par `BASE_URL`
- Le bot Discord génère tous ses liens dynamiquement via `settings.base_url`
- Nginx (dans le container) utilise `server_name _` (wildcard) — Traefik gère le routage en amont
- Les URLs frontend sont toutes relatives → aucun changement côté front
- Les images Docker restent `ghcr.io/bubu31/yoto-library-*` pour l'instant (même CI/CD)
- Le même `SECRET_KEY` est utilisé sur prod et staging pour la compatibilité des tokens
