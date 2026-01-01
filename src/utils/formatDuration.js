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
  // Essaie d'abord la durée totale depuis les métadonnées
  if (playlist?.metadata?.media?.duration) {
    return playlist.metadata.media.duration;
  }

  if (!playlist?.content?.chapters) return 0;

  let total = 0;

  for (const chapter of playlist.content.chapters) {
    // Utilise la durée du chapter si disponible
    if (chapter.duration) {
      total += chapter.duration;
    } else if (chapter.tracks) {
      // Sinon, somme les durées des tracks
      for (const track of chapter.tracks) {
        total += track.duration || 0;
      }
    }
  }

  return total;
}

/**
 * Extrait toutes les pistes d'une playlist
 * Les tracks n'ont pas de titre dans l'API Yoto, on utilise le titre du chapter
 * ou on génère un nom "Piste X"
 * @param {object} playlist
 * @returns {Array} Liste des pistes avec leurs titres
 */
export function extractAllTracks(playlist) {
  if (!playlist?.content?.chapters) return [];

  const tracks = [];
  let globalTrackIndex = 1;

  for (const chapter of playlist.content.chapters) {
    // Si le chapter a des tracks, on les ajoute
    if (chapter.tracks && chapter.tracks.length > 0) {
      for (const track of chapter.tracks) {
        tracks.push({
          // Utilise le titre du chapter s'il n'y a qu'une track, sinon génère un nom
          title: chapter.title || `Piste ${globalTrackIndex}`,
          duration: track.duration || chapter.duration || 0,
          chapterTitle: chapter.title,
        });
        globalTrackIndex++;
      }
    } else if (chapter.title) {
      // Si pas de tracks mais un chapter avec titre (et potentiellement une durée)
      tracks.push({
        title: chapter.title,
        duration: chapter.duration || 0,
        chapterTitle: chapter.title,
      });
      globalTrackIndex++;
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
