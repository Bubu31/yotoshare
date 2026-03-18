# YotoShare - Project Guide

## Overview

Application full-stack de gestion et partage d'archives audio MYO Studio avec intégration Discord.
Permet l'upload, l'édition (chapitres, audio, covers, NFO) et la publication d'archives sur un forum Discord.

**Domaine production** : `yotoshare.com` (ancien : `lib.yoto.webuso.fr`, redirect 301 en place)
**Repo** : `github.com/bubu31/yotoshare` — branche principale : `main`, ancienne branche : `legacy`

## Stack technique

| Couche | Technologies |
|--------|-------------|
| Backend | FastAPI 0.109, SQLAlchemy 2.0, SQLite, Python 3.11 |
| Frontend | Vue 3.4, Pinia 2.1, Vue Router 4.2, Tailwind CSS 3.4, Vite 5 |
| Audio | FFmpeg (waveform, split, trim, merge via subprocess) |
| Discord | py-cord 2.4 (bot dans un thread background) |
| Infra | Docker Compose, Traefik (reverse proxy, TLS), Komodo (orchestration) |
| CI/CD | GitHub Actions → GHCR (`ghcr.io/bubu31/yotoshare-backend/frontend/nginx`) |

## Structure du projet

```
backend/app/
├── main.py              # App FastAPI, enregistrement des routers, startup
├── config.py            # Settings Pydantic (lit .env) — BASE_URL centralisé ici
├── database.py          # SQLAlchemy engine, sessions, migrations manuelles
├── models.py            # Modèles ORM (Archive, Category, Age, User, Role, DownloadToken, Pack, PackAsset)
├── schemas.py           # Schémas Pydantic request/response
├── auth.py              # JWT (HS256, 24h), bcrypt, get_current_user, require_admin
├── routers/             # Endpoints API
│   ├── __init__.py      # Exporte tous les routers
│   ├── auth.py          # Login
│   ├── archives.py      # CRUD archives
│   ├── categories.py    # CRUD catégories
│   ├── ages.py          # CRUD âges
│   ├── download.py      # Tokens et téléchargement
│   ├── discord.py       # Publication Discord
│   ├── share.py         # Pages de partage (OG meta)
│   ├── packs.py         # Packs d'archives
│   ├── users.py         # Gestion utilisateurs
│   └── roles.py         # Gestion rôles/permissions
└── services/
    ├── storage.py        # Upload/download fichiers, extraction metadata ZIP
    ├── archive_editor.py # Édition ZIP (context manager), MYO Studio compat
    ├── audio_processor.py # FFmpeg: durée, waveform, split, trim, merge
    ├── discord_bot.py    # Bot py-cord, publish, bouton download, forum tags
    ├── token.py          # Tokens de téléchargement signés HMAC-SHA256
    └── pack_image.py     # Génération images de packs

frontend/src/
├── main.js              # Point d'entrée Vue
├── router/index.js      # Routes
├── services/api.js      # Instance Axios, intercepteur 401
├── composables/         # useMessage.js
├── stores/              # Pinia: auth.js, archives.js, packs.js, theme.js
├── views/               # ArchivesView, UploadView, EditView, PacksView, etc.
└── components/
    ├── Navbar.vue, ArchiveCard.vue, ArchiveForm.vue, TagInput.vue
    ├── BulkUploadModal.vue, PublishModal.vue, CreatePackModal.vue
    └── archive-editor/  # ChapterList, ChapterEditor, AudioWaveform, CoverCropper, NfoEditor

nginx/
├── nginx.conf           # Reverse proxy config (rate limiting, gzip, timeouts)
└── Dockerfile           # Build nginx image avec config embarquée

.github/workflows/
└── ci.yml               # Test + build/push 3 images Docker sur GHCR (main → :latest, staging → :staging)
```

## Conventions et patterns

### Backend

- **Routers** : déclarés dans `routers/`, exportés via `__init__.py`, enregistrés dans `main.py`
- **Auth** : JWT HTTPBearer. Dépendances `get_current_user` (tous auth) et `require_admin` (admin only)
- **Rôles** : `admin` (accès complet) et `editor` (pas de DELETE)
- **Migrations** : SQL brut dans `database.py:run_migrations()` (pas d'Alembic)
- **Admin seed** : créé au démarrage depuis `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` (.env)
- **Fichiers** : archives = `{NAS_MOUNT_PATH}/archives/{uuid}.zip`, covers = `{NAS_MOUNT_PATH}/covers/{uuid}.jpg`
- **Format ZIP** : dossier racine optionnel, contient `data/card-data.json` avec metadata/chapitres
- **Tokens download** : `{random_hex}{hmac_signature}`, usage unique, expiration configurable
- **URLs dynamiques** : toutes les URLs (share, download, Discord embeds) utilisent `settings.base_url`

### Frontend

- **State** : Pinia stores (auth persiste token/role dans localStorage, theme persiste dark mode)
- **API** : Axios avec intercepteur 401 → redirect `/login`. URLs toutes relatives (pas de domaine hardcodé)
- **Icônes UI** : Font Awesome 6.5.1 via CDN
- **Style** : Tailwind CSS avec dark mode par classe, palette primary sky blue
- **Couleurs dynamiques Tailwind** : utiliser des objets de mapping statiques — jamais de template literals pour les classes Tailwind
- **Éditeur** : wavesurfer.js (audio), vue-advanced-cropper (cover), vuedraggable (chapitres)
- **Composables** : `useMessage()` pour les notifications (utilisé dans toutes les views)

## Routes API

| Méthode | Chemin | Auth | Description |
|---------|--------|------|-------------|
| POST | `/api/auth/login` | Non | Connexion, retourne JWT + rôle |
| GET/POST | `/api/archives` | GET=Non, POST=Oui | Liste / Création d'archive |
| PUT | `/api/archives/{id}` | Oui | Mise à jour metadata |
| DELETE | `/api/archives/{id}` | Admin | Suppression archive + fichiers |
| GET | `/api/archives/{id}/content` | Oui | Structure éditable du ZIP |
| POST | `/api/archives/{id}/chapters` | Oui | Mise à jour chapitres |
| PUT | `/api/archives/{id}/audio/{key}` | Oui | Édition audio (split/trim/merge) |
| GET/POST/DELETE | `/api/categories` | Varies | CRUD catégories (DELETE=admin) |
| GET/POST/DELETE | `/api/ages` | Varies | CRUD tranches d'âge (DELETE=admin) |
| GET/POST/DELETE | `/api/users` | Admin | CRUD utilisateurs |
| GET/POST/DELETE | `/api/roles` | Admin | CRUD rôles |
| POST | `/api/download/token` | Oui | Créer token de téléchargement |
| GET | `/api/download/{token}` | Non | Stream fichier archive |
| POST | `/api/discord/publish` | Oui | Publier sur forum Discord |
| GET/POST/DELETE | `/api/packs` | Oui | CRUD packs d'archives |

## Commandes de développement

```bash
# Backend (local)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (local)
cd frontend && npm install
npm run dev          # Dev server avec proxy /api → localhost:8000

# Docker (production)
docker compose up --build -d
```

## Variables d'environnement (.env)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète pour JWT et signatures HMAC |
| `ADMIN_USERNAME` | Username admin seedé au démarrage |
| `ADMIN_PASSWORD_HASH` | Hash bcrypt du mot de passe admin |
| `NAS_MOUNT_PATH` | Chemin montage NAS pour stockage fichiers |
| `DISCORD_BOT_TOKEN` | Token du bot Discord |
| `DISCORD_GUILD_ID` | ID du serveur Discord |
| `DISCORD_FORUM_CHANNEL_ID` | ID du canal forum Discord |
| `BASE_URL` | URL publique de l'application (prod: `https://yotoshare.com`) |
| `DOWNLOAD_LINK_EXPIRY` | Durée de validité des liens (secondes, défaut: 7200) |
| `CORS_ORIGINS` | Origines CORS autorisées |
| `SERVICE_API_KEY` | Clé API inter-service (ex: yotoprint) |
| `YOTO_CLIENT_ID` | Client ID Yoto OAuth |
| `YOTO_REDIRECT_URI` | URI de callback OAuth |
| `AI_API_URL` | URL de l'API IA externe |
| `AI_API_KEY` | Clé API IA |

## Infra & Déploiement

### Docker local (docker-compose.yml)
- **backend** : build local, healthcheck `/api/health`
- **frontend** : build Vite → Nginx statique, healthcheck
- **nginx** : `nginx:alpine` avec config montée en volume
- **autoheal** : redémarre les containers unhealthy

### Production (Komodo sur komodo.busolin.fr)

3 stacks configurées :

| Stack | Domaine | Images | État |
|-------|---------|--------|------|
| `yotoshare` | `yotoshare.com` | `ghcr.io/bubu31/yotoshare-*:latest` | Config prête, non déployée |
| `yoto-library` | `lib.yoto.webuso.fr` | `ghcr.io/bubu31/yoto-library-*:latest` | Prod actuelle |
| `yoto-library-staging` | `staging.yotoshare.com` | `ghcr.io/bubu31/yotoshare-*:staging` | Config prête, non déployée |

- **Traefik** : gère TLS (Let's Encrypt) et routage. Redirect 301 `lib.yoto.webuso.fr` → `yotoshare.com` configurée via labels sur le stack `yotoshare`
- **NFS** : volume NFS vers Synology NAS (`192.168.1.120:/volume10/yoto`)
- **CI/CD** : push sur `main` → build + push `:latest` sur GHCR. Push sur `staging` → `:staging`
- **Variable GitHub Actions requise** : `VITE_YOTO_CLIENT_ID` (Settings > Variables > Actions)

### Migration en cours (voir todo.md)
- La prod actuelle tourne sur `lib.yoto.webuso.fr` (stack `yoto-library`)
- Le stack `yotoshare` est prêt à remplacer sur `yotoshare.com`
- Le DNS de `lib.yoto.webuso.fr` doit pointer vers le même serveur pour que la redirect fonctionne
- Le même `SECRET_KEY` doit être conservé pour la validité des tokens existants
