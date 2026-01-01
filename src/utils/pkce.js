// Génération PKCE (Proof Key for Code Exchange)
// Requis pour OAuth 2.0 Public Client

/**
 * Génère un code_verifier aléatoire
 * @returns {string} Code verifier de 43-128 caractères
 */
export function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

/**
 * Génère le code_challenge à partir du verifier
 * @param {string} verifier - Le code_verifier
 * @returns {Promise<string>} Le code_challenge (SHA256 + base64url)
 */
export async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(digest));
}

/**
 * Encode en base64url (sans padding)
 * @param {Uint8Array} buffer 
 * @returns {string}
 */
function base64URLEncode(buffer) {
  const base64 = btoa(String.fromCharCode(...buffer));
  return base64
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Génère un state aléatoire pour prévenir CSRF
 * @returns {string}
 */
export function generateState() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}
