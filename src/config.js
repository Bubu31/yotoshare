// Configuration YotoShare
export const CONFIG = {
  // OAuth Yoto
  clientId: import.meta.env.VITE_YOTO_CLIENT_ID || 'leWzZrQzieWfwQ0dXEkwu0tAnHZtDu4n',
  redirectUri: import.meta.env.VITE_YOTO_REDIRECT_URI || 'https://yoto.busolin.fr/callback',
  
  // API Yoto
  apiUrl: import.meta.env.VITE_YOTO_API_URL || 'https://api.yotoplay.com',
  authUrl: 'https://login.yotoplay.com/authorize',
  tokenUrl: 'https://login.yotoplay.com/oauth/token',
  audience: 'https://api.yotoplay.com',
  
  // App
  appName: 'YotoShare',
  signature: 'Partagé par Mathieu',
  
  // Design
  colors: {
    primary: '#F95E3F',
    primaryLight: '#FF8A65',
    bgDark: '#1a1a2e',
    bgPanel: '#16213e',
  },
  
  // Export
  exportWidth: 940,
  exportHeight: 788,
};

export const COLOR_PRESETS = [
  { name: 'Orange Yoto', color: '#F95E3F', bg: 'linear-gradient(135deg, #F95E3F 0%, #FF8A65 100%)' },
  { name: 'Bleu Océan', color: '#0077B6', bg: 'linear-gradient(135deg, #0077B6 0%, #90E0EF 100%)' },
  { name: 'Vert Jungle', color: '#2D6A4F', bg: 'linear-gradient(135deg, #2D6A4F 0%, #95D5B2 100%)' },
  { name: 'Rose Bonbon', color: '#E63946', bg: 'linear-gradient(135deg, #E63946 0%, #FFC8DD 100%)' },
  { name: 'Violet Magic', color: '#7B2CBF', bg: 'linear-gradient(135deg, #7B2CBF 0%, #E0AAFF 100%)' },
  { name: 'Jaune Soleil', color: '#F4A261', bg: 'linear-gradient(135deg, #E76F51 0%, #F4D35E 100%)' },
];
