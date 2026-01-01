import { useState, useEffect, useCallback } from 'react';
import { CONFIG } from '../config';
import { generateCodeVerifier, generateCodeChallenge, generateState } from '../utils/pkce';
import { yotoAPI } from '../utils/api';

const STORAGE_KEYS = {
  accessToken: 'yotoshare_access_token',
  refreshToken: 'yotoshare_refresh_token',
  expiresAt: 'yotoshare_expires_at',
  codeVerifier: 'yotoshare_code_verifier',
  state: 'yotoshare_state',
};

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);

  // Vérifie si le token est expiré
  const isTokenExpired = useCallback(() => {
    const expiresAt = localStorage.getItem(STORAGE_KEYS.expiresAt);
    if (!expiresAt) return true;
    return Date.now() > parseInt(expiresAt, 10);
  }, []);

  // Charge les tokens depuis le localStorage
  const loadTokens = useCallback(async () => {
    const storedAccessToken = localStorage.getItem(STORAGE_KEYS.accessToken);
    const storedRefreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);

    if (!storedAccessToken) {
      setIsLoading(false);
      return;
    }

    // Si le token est expiré, essayer de le rafraîchir
    if (isTokenExpired() && storedRefreshToken) {
      try {
        const tokens = await yotoAPI.refreshToken(storedRefreshToken);
        saveTokens(tokens);
        setAccessToken(tokens.access_token);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Erreur refresh token:', error);
        logout();
      }
    } else if (!isTokenExpired()) {
      setAccessToken(storedAccessToken);
      setIsAuthenticated(true);
    }

    setIsLoading(false);
  }, [isTokenExpired]);

  // Sauvegarde les tokens
  const saveTokens = (tokens) => {
    localStorage.setItem(STORAGE_KEYS.accessToken, tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem(STORAGE_KEYS.refreshToken, tokens.refresh_token);
    }
    // Calcule l'expiration (expires_in est en secondes)
    const expiresAt = Date.now() + (tokens.expires_in * 1000);
    localStorage.setItem(STORAGE_KEYS.expiresAt, expiresAt.toString());
  };

  // Démarre le flow OAuth
  const login = async () => {
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = await generateCodeChallenge(codeVerifier);
    const state = generateState();

    // Stocke le verifier et state pour le callback
    localStorage.setItem(STORAGE_KEYS.codeVerifier, codeVerifier);
    localStorage.setItem(STORAGE_KEYS.state, state);

    // Construit l'URL d'autorisation
    const params = new URLSearchParams({
      audience: CONFIG.audience,
      scope: 'offline_access',
      response_type: 'code',
      client_id: CONFIG.clientId,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      redirect_uri: CONFIG.redirectUri,
      state: state,
    });

    window.location.href = `${CONFIG.authUrl}?${params.toString()}`;
  };

  // Gère le callback OAuth
  const handleCallback = async (code, returnedState) => {
    const storedState = localStorage.getItem(STORAGE_KEYS.state);
    const codeVerifier = localStorage.getItem(STORAGE_KEYS.codeVerifier);

    // Vérifie le state pour prévenir CSRF
    if (returnedState !== storedState) {
      throw new Error('State invalide - possible attaque CSRF');
    }

    if (!codeVerifier) {
      throw new Error('Code verifier manquant');
    }

    // Échange le code contre des tokens
    const tokens = await yotoAPI.exchangeCodeForToken(code, codeVerifier);
    saveTokens(tokens);

    // Nettoie les données temporaires
    localStorage.removeItem(STORAGE_KEYS.codeVerifier);
    localStorage.removeItem(STORAGE_KEYS.state);

    setAccessToken(tokens.access_token);
    setIsAuthenticated(true);

    return tokens;
  };

  // Déconnexion
  const logout = () => {
    localStorage.removeItem(STORAGE_KEYS.accessToken);
    localStorage.removeItem(STORAGE_KEYS.refreshToken);
    localStorage.removeItem(STORAGE_KEYS.expiresAt);
    setAccessToken(null);
    setIsAuthenticated(false);
    setUser(null);
  };

  // Récupère un token valide (refresh si nécessaire)
  const getValidToken = async () => {
    if (!isTokenExpired()) {
      return localStorage.getItem(STORAGE_KEYS.accessToken);
    }

    const refreshToken = localStorage.getItem(STORAGE_KEYS.refreshToken);
    if (!refreshToken) {
      logout();
      throw new Error('Session expirée');
    }

    try {
      const tokens = await yotoAPI.refreshToken(refreshToken);
      saveTokens(tokens);
      setAccessToken(tokens.access_token);
      return tokens.access_token;
    } catch (error) {
      logout();
      throw new Error('Session expirée');
    }
  };

  // Charge les tokens au montage
  useEffect(() => {
    loadTokens();
  }, [loadTokens]);

  return {
    isAuthenticated,
    isLoading,
    user,
    accessToken,
    login,
    logout,
    handleCallback,
    getValidToken,
  };
}

export default useAuth;
