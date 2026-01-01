# CLAUDE.md - YotoShare

## 🎯 Contexte du projet

**YotoShare** est une application web React permettant de générer des visuels stylisés pour partager des playlists Yoto MYO sur les réseaux sociaux (Facebook, groupes communautaires).

### Fonctionnalités principales
- Authentification OAuth 2.0 avec l'API Yoto (PKCE flow)
- Récupération automatique des playlists MYO de l'utilisateur
- Génération de visuels "carte" personnalisés avec :
  - Couverture de la playlist
  - Titre
  - Liste des pistes
  - Durée totale
  - Signature "Partagé par Mathieu"
- Export PNG pour partage sur réseaux sociaux
- Palette de couleurs adaptable au contenu

### Utilisateur cible
Mathieu, membre d'une communauté Facebook de partage de playlists Yoto.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  Docker (yoto.busolin.fr)                           │
│  ┌───────────────────────────────────────────────┐  │
│  │  Nginx (sert le build React)                  │  │
│  │  - SPA avec React Router                      │  │
│  │  - Toutes les routes → index.html             │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │
         ▼ OAuth PKCE + API REST
┌─────────────────────┐
│  api.yotoplay.com   │
│  - /oauth/authorize │
│  - /oauth/token     │
│  - /card/mine       │
│  - /card/{id}       │
└─────────────────────┘
```

---

## 🛠️ Stack technique

| Technologie | Usage |
|-------------|-------|
| **React 18** | Framework UI |
| **Vite** | Build tool |
| **React Router 6** | Routing SPA |
| **Tailwind CSS** | Styling |
| **html-to-image** | Export PNG des cartes |
| **file-saver** | Téléchargement des images |
| **Docker + Nginx** | Hébergement |
| **Traefik** | Reverse proxy + SSL |

---

## 📡 API Yoto utilisée

### Authentification (OAuth 2.0 PKCE)
```
GET https://api.yotoplay.com/oauth/authorize
  ?client_id=leWzZrQzieWfwQ0dXEkwu0tAnHZtDu4n
  &redirect_uri=https://yoto.busolin.fr/callback
  &response_type=code
  &scope=openid profile
  &code_challenge={challenge}
  &code_challenge_method=S256

POST https://api.yotoplay.com/oauth/token
  - grant_type=authorization_code
  - code={code}
  - redirect_uri=...
  - client_id=...
  - code_verifier={verifier}
```

### Endpoints data
```
GET /card/mine
  → Liste des playlists MYO de l'utilisateur
  → Headers: Authorization: Bearer {access_token}

GET /card/{cardId}
  → Détails d'une playlist (chapitres, pistes, durées)
  → Headers: Authorization: Bearer {access_token}
```

### Structure d'une playlist
```json
{
  "card": {
    "cardId": "xxx",
    "title": "Kung Fu Panda",
    "metadata": {
      "cover": { "imageUrl": "https://..." }
    },
    "content": {
      "chapters": [
        {
          "title": "Chapter 1",
          "tracks": [
            {
              "title": "Introduction",
              "duration": 180,
              "fileSize": 1536000
            }
          ]
        }
      ]
    }
  }
}
```

---

## 📁 Structure des fichiers

```
yotoshare/
├── src/
│   ├── main.jsx              # Point d'entrée React
│   ├── App.jsx               # Router principal
│   ├── index.css             # Styles Tailwind
│   ├── config.js             # Config OAuth (client_id, etc.)
│   │
│   ├── hooks/
│   │   └── useAuth.js        # Hook auth + token management
│   │
│   ├── pages/
│   │   ├── Home.jsx          # Page d'accueil / login
│   │   ├── Callback.jsx      # Gestion retour OAuth
│   │   ├── Dashboard.jsx     # Liste des playlists
│   │   └── Generator.jsx     # Génération du visuel
│   │
│   ├── components/
│   │   ├── PlaylistCard.jsx  # Aperçu playlist dans la liste
│   │   ├── CardPreview.jsx   # Visuel généré (le composant principal)
│   │   ├── ColorPicker.jsx   # Sélecteur de palette
│   │   └── ExportButton.jsx  # Bouton téléchargement PNG
│   │
│   └── utils/
│       ├── pkce.js           # Génération code_verifier/challenge
│       ├── api.js            # Appels API Yoto
│       └── formatDuration.js # Helpers format durée
│
├── public/
│   ├── logo.svg              # Logo YotoShare
│   ├── tonie-logo.svg        # Logo source Tonie
│   ├── yoto-logo.svg         # Logo source Yoto
│   └── myo-studio-badge.svg  # Badge Archive MYO Studio
│
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── package.json
│
├── Dockerfile
├── docker-compose.yml        # Avec labels Traefik
├── nginx.conf                # Config Nginx pour SPA
│
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md                 # Ce fichier
```

---

## 🚀 Commandes utiles

### Développement local
```bash
# Installation
npm install

# Lancer le dev server
npm run dev
# → http://localhost:3000

# Build production
npm run build

# Preview du build
npm run preview
```

### Docker
```bash
# Build et démarrage
docker compose up -d --build

# Logs
docker compose logs -f

# Arrêt
docker compose down

# Rebuild après changements
docker compose up -d --build --force-recreate
```

---

## 🔧 Configuration

### Variables d'environnement (.env)
```env
VITE_YOTO_CLIENT_ID=leWzZrQzieWfwQ0dXEkwu0tAnHZtDu4n
VITE_YOTO_REDIRECT_URI=https://yoto.busolin.fr/callback
VITE_YOTO_API_URL=https://api.yotoplay.com
```

### Traefik labels (docker-compose.yml)
- Host: `yoto.busolin.fr`
- HTTPS automatique via Let's Encrypt
- Réseau: `traefik` (à adapter selon ta config)

---

## 🎨 Design & DA

### Palette de couleurs
| Nom | Hex | Usage |
|-----|-----|-------|
| Orange Yoto | `#F95E3F` | Couleur principale |
| Orange clair | `#FF8A65` | Gradient |
| Fond sombre | `#1a1a2e` | Background app |
| Panel | `#16213e` | Panneaux/cartes |

### Signature
Tous les visuels générés incluent "✨ Partagé par Mathieu" en bas à gauche.

### Format export
- **Dimensions**: 940×788px (optimisé Facebook)
- **Format**: PNG

---

## 🔄 Pour étendre le projet

### Ajouter un nouveau template de carte
1. Créer un nouveau composant dans `src/components/templates/`
2. L'ajouter au sélecteur dans `Generator.jsx`
3. Respecter les props: `{ playlist, accentColor, signature }`

### Ajouter une nouvelle palette
Modifier `src/components/ColorPicker.jsx` :
```javascript
const colorPresets = [
  { name: 'Orange Yoto', color: '#F95E3F', bg: 'linear-gradient(...)' },
  // Ajouter ici
];
```

### Changer la signature
Modifier dans `src/config.js` :
```javascript
export const SIGNATURE = "Partagé par Mathieu";
```

### Supporter d'autres formats d'export
- Modifier `ExportButton.jsx`
- Utiliser `html-to-image` avec options différentes (JPEG, dimensions)

---

## 🐛 Debugging

### Token expiré
Les access tokens Yoto expirent après quelques heures. L'app utilise le refresh token automatiquement. Si problème, déconnecter/reconnecter.

### CORS
Pas de problème CORS car l'app est full client-side et Yoto autorise les appels depuis les domaines configurés dans le portail développeur.

### OAuth callback échoue
Vérifier que l'URL exacte `https://yoto.busolin.fr/callback` est bien dans les "Allowed Callback URLs" du portail Yoto.

---

## 📚 Ressources

- **API Yoto**: https://yoto.dev/api/
- **Auth Yoto**: https://yoto.dev/authentication/auth/
- **Portail développeur**: https://yoto.dev/
- **Discord Yoto Dev**: https://discord.gg/FkwBpYf2CN

---

## 🚀 Déploiement

### Pipeline CI/CD
1. Push sur `master` → GitHub Action build l'image Docker
2. Image poussée sur `ghcr.io/bubu31/yotoshare:latest`
3. Déployer via Komodo : `mcp__komodo__deploy_stack` avec `stack_name: "yotoshare"`

### Vérifier le statut
```bash
gh run list --limit 1  # Vérifier GitHub Action
```

---

## 🏷️ Système de tags spéciaux

### Tags `ys:` (YotoShare)
Les tags préfixés par `ys:` sont des tags système, filtrés de l'affichage mais utilisés par l'application :

- **`ys:color:#XXXXXX`** : Sauvegarde la couleur d'accent sélectionnée
  - Sauvegardé automatiquement avec les métadonnées
  - Restauré au chargement de la playlist
  - Ne s'affiche pas sur le visuel

### Sources auto-détectées
Les tags correspondant aux sources (YouTube, Tonie, Yoto, Spotify, Podcast) sont automatiquement détectés au chargement et pré-sélectionnés dans l'interface.

---

## 🎨 Assets visuels

### Logos sources (public/)
- `tonie-logo.svg` - Logo Toniebox (turquoise)
- `yoto-logo.svg` - Logo Yoto (orange)

### Badge Archive MYO Studio
- `myo-studio-badge.svg` - Logo cercle orange avec note de musique
- Affiché en haut à droite de tous les visuels exportés
- Position : `top-5 right-5`, taille icône : `w-10 h-10`

---

## 📝 Historique

- **v1.0** - Version initiale avec OAuth + génération de cartes
- **v1.1** - Ajout sauvegarde couleur dans tags `ys:color:`
- **v1.2** - Logos Tonie/Yoto pour les sources
- **v1.3** - Badge "Archive MYO Studio" en haut à droite
- Créé avec l'aide de Claude (Anthropic)
