/**
 * Formate une durée en secondes vers un format lisible
 * @param {number} seconds - Durée en secondes
 * @returns {string} Format "Xh Xm Xs" ou "Xm Xs"
 */
export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  const parts = [];
  
  if (hours > 0) {
    parts.push(`${hours}h`);
  }
  
  if (minutes > 0) {
    parts.push(`${minutes}m`);
  }
  
  if (secs > 0 && hours === 0) {
    parts.push(`${secs}s`);
  }
  
  return parts.join(' ') || '0s';
}

/**
 * Formate une durée courte (pour les pistes)
 * @param {number} seconds 
 * @returns {string} Format "MM:SS"
 */
export function formatTrackDuration(seconds) {
  if (!seconds || seconds <= 0) return '0:00';
  
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Calcule la durée totale d'une playlist
 * @param {object} playlist - Objet playlist avec chapters/tracks
 * @returns {number} Durée totale en secondes
 */
export function calculateTotalDuration(playlist) {
  if (!playlist?.content?.chapters) return 0;
  
  let total = 0;
  
  for (const chapter of playlist.content.chapters) {
    if (chapter.tracks) {
      for (const track of chapter.tracks) {
        total += track.duration || 0;
      }
    }
  }
  
  return total;
}

/**
 * Extrait toutes les pistes d'une playlist
 * @param {object} playlist 
 * @returns {Array} Liste des pistes avec leurs titres
 */
export function extractAllTracks(playlist) {
  if (!playlist?.content?.chapters) return [];
  
  const tracks = [];
  
  for (const chapter of playlist.content.chapters) {
    if (chapter.tracks) {
      for (const track of chapter.tracks) {
        tracks.push({
          title: track.title,
          duration: track.duration,
          chapterTitle: chapter.title,
        });
      }
    }
  }
  
  return tracks;
}

/**
 * Formate la taille d'un fichier
 * @param {number} bytes 
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 MB';
  
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}
