# 🎨 YotoShare

Créez et partagez de jolis visuels de vos playlists Yoto MYO en quelques clics.

![Logo YotoShare](public/logo.svg)

## ✨ Fonctionnalités

- 🔐 Connexion sécurisée avec votre compte Yoto (OAuth)
- 📚 Liste automatique de vos playlists MYO
- 🎨 Génération de visuels stylés personnalisables
- 🎨 6 palettes de couleurs
- 📥 Export PNG optimisé pour Facebook (940×788px)
- ✨ Signature personnalisée "Partagé par Mathieu"

## 🚀 Installation

### Prérequis

- Docker & Docker Compose
- Traefik configuré avec Let's Encrypt
- Un réseau Docker `traefik`

### Déploiement

1. **Cloner le repo**
   ```bash
   git clone <your-repo>
   cd yotoshare
   ```

2. **Vérifier la configuration**
   ```bash
   # Le fichier .env est déjà configuré
   cat .env
   ```

3. **Lancer l'application**
   ```bash
   docker compose up -d --build
   ```

4. **Vérifier que tout fonctionne**
   ```bash
   docker compose logs -f
   ```

L'application sera disponible sur https://yoto.busolin.fr

## 🛠️ Développement local

```bash
# Installation des dépendances
npm install

# Lancer le serveur de dev
npm run dev
# → http://localhost:3000

# Build de production
npm run build

# Preview du build
npm run preview
```

## 📁 Structure du projet

```
yotoshare/
├── src/
│   ├── main.jsx              # Point d'entrée
│   ├── App.jsx               # Router
│   ├── config.js             # Configuration
│   ├── hooks/useAuth.js      # Authentification
│   ├── pages/                # Pages de l'app
│   └── utils/                # Helpers
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── CLAUDE.md                 # Doc pour Claude Code
```

## 🔧 Configuration Yoto

L'application est configurée avec :
- **Client ID**: `leWzZrQzieWfwQ0dXEkwu0tAnHZtDu4n`
- **Callback URL**: `https://yoto.busolin.fr/callback`

## 📝 Licence

Projet personnel créé par Mathieu.

## 🙏 Crédits

- API Yoto : https://yoto.dev
- Créé avec l'aide de Claude (Anthropic)
