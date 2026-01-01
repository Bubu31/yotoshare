import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { yotoAPI } from '../utils/api';
import { CONFIG } from '../config';
import { formatDuration, calculateTotalDuration, extractAllTracks } from '../utils/formatDuration';

export default function Dashboard() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, logout, getValidToken } = useAuth();
  const [playlists, setPlaylists] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    const fetchPlaylists = async () => {
      if (!isAuthenticated) return;
      
      try {
        setIsLoading(true);
        const token = await getValidToken();
        const data = await yotoAPI.getMyPlaylists(token);
        setPlaylists(data);
      } catch (err) {
        console.error('Erreur chargement playlists:', err);
        setError('Impossible de charger vos playlists');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlaylists();
  }, [isAuthenticated, getValidToken]);

  const handleSelectPlaylist = (playlist) => {
    navigate(`/generate/${playlist.cardId}`, { state: { playlist } });
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-orange-400 flex items-center justify-center">
              <span className="text-white font-bold text-lg">Y</span>
            </div>
            <span className="text-white font-semibold text-lg">{CONFIG.appName}</span>
          </div>
          
          <button
            onClick={logout}
            className="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Déconnexion</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Vos playlists MYO</h1>
          <p className="text-slate-400">Sélectionnez une playlist pour générer un visuel de partage</p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-slate-800/50 rounded-2xl p-4 animate-pulse">
                <div className="w-full aspect-square bg-slate-700 rounded-xl mb-4" />
                <div className="h-6 bg-slate-700 rounded w-3/4 mb-2" />
                <div className="h-4 bg-slate-700 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8 text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all"
            >
              Réessayer
            </button>
          </div>
        ) : playlists.length === 0 ? (
          <div className="bg-slate-800/50 rounded-2xl p-12 text-center">
            <div className="w-20 h-20 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-10 h-10 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Aucune playlist MYO</h3>
            <p className="text-slate-400">
              Créez des playlists "Make Your Own" sur l'app Yoto pour les voir apparaître ici
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {playlists.map((playlist) => (
              <PlaylistCard
                key={playlist.cardId}
                playlist={playlist}
                onClick={() => handleSelectPlaylist(playlist)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function PlaylistCard({ playlist, onClick }) {
  const coverUrl = playlist.metadata?.cover?.imageUrl;
  const tracks = extractAllTracks(playlist);
  const totalDuration = calculateTotalDuration(playlist);

  return (
    <button
      onClick={onClick}
      className="bg-slate-800/50 hover:bg-slate-700/50 rounded-2xl p-4 text-left transition-all duration-200 hover:scale-[1.02] hover:shadow-xl border border-transparent hover:border-orange-500/30 group"
    >
      {/* Cover */}
      <div className="w-full aspect-square bg-slate-700 rounded-xl mb-4 overflow-hidden relative">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={playlist.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-6xl">🎵</span>
          </div>
        )}
        
        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-4">
          <span className="px-4 py-2 bg-orange-500 text-white text-sm font-semibold rounded-full flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            Générer un visuel
          </span>
        </div>
      </div>

      {/* Info */}
      <h3 className="text-white font-semibold text-lg mb-2 truncate">{playlist.title}</h3>
      
      <div className="flex items-center gap-4 text-slate-400 text-sm">
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
          {tracks.length} pistes
        </span>
        
        <span className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {formatDuration(totalDuration)}
        </span>
      </div>
    </button>
  );
}
