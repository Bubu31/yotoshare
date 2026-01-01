import { CONFIG } from '../config';

/**
 * Client API Yoto
 */
class YotoAPI {
  constructor() {
    this.baseUrl = CONFIG.apiUrl;
  }

  /**
   * Headers avec authentification
   */
  getHeaders(accessToken) {
    return {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    };
  }

  /**
   * Récupère les playlists MYO de l'utilisateur
   */
  async getMyPlaylists(accessToken) {
    const response = await fetch(`${this.baseUrl}/card/mine`, {
      headers: this.getHeaders(accessToken),
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    const data = await response.json();
    return data.cards || [];
  }

  /**
   * Récupère les détails d'une playlist
   */
  async getPlaylistDetails(accessToken, cardId) {
    const response = await fetch(`${this.baseUrl}/card/${cardId}`, {
      headers: this.getHeaders(accessToken),
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    const data = await response.json();
    return data.card;
  }

  /**
   * Récupère le profil utilisateur
   */
  async getUserProfile(accessToken) {
    const response = await fetch(`${this.baseUrl}/user/me`, {
      headers: this.getHeaders(accessToken),
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    return response.json();
  }

  /**
   * Échange le code OAuth contre des tokens
   */
  async exchangeCodeForToken(code, codeVerifier) {
    const response = await fetch(CONFIG.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: CONFIG.clientId,
        code: code,
        redirect_uri: CONFIG.redirectUri,
        code_verifier: codeVerifier,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Erreur token: ${error}`);
    }

    return response.json();
  }

  /**
   * Rafraîchit l'access token
   */
  async refreshToken(refreshToken) {
    const response = await fetch(CONFIG.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: CONFIG.clientId,
        refresh_token: refreshToken,
      }),
    });

    if (!response.ok) {
      throw new Error('Impossible de rafraîchir le token');
    }

    return response.json();
  }
}

export const yotoAPI = new YotoAPI();
export default yotoAPI;
