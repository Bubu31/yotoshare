import { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { toPng } from 'html-to-image';
import useAuth from '../hooks/useAuth';
import { yotoAPI } from '../utils/api';
import { CONFIG, COLOR_PRESETS } from '../config';
import { formatDuration, formatTrackDuration, calculateTotalDuration, extractAllTracks } from '../utils/formatDuration';

export default function Generator() {
  const { cardId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const cardRef = useRef(null);
  
  const { getValidToken } = useAuth();
  // Utilise les données du Dashboard pour l'affichage initial (titre, cover)
  const initialData = location.state?.playlist || null;
  const [playlist, setPlaylist] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [accentColor, setAccentColor] = useState(COLOR_PRESETS[0].color);
  const [error, setError] = useState(null);

  const selectedPreset = COLOR_PRESETS.find(p => p.color === accentColor) || COLOR_PRESETS[0];

  // Toujours fetch les détails complets pour avoir les chapters/tracks
  useEffect(() => {
    let isMounted = true;

    const fetchPlaylist = async () => {
      try {
        setIsLoading(true);
        const token = await getValidToken();
        if (!isMounted) return;
        const data = await yotoAPI.getPlaylistDetails(token, cardId);
        console.log('Playlist details:', data);
        if (!isMounted) return;
        setPlaylist(data);
      } catch (err) {
        console.error('Erreur chargement playlist:', err);
        if (isMounted) {
          setError('Impossible de charger cette playlist');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchPlaylist();

    return () => {
      isMounted = false;
    };
  }, [cardId]);

  const handleExport = async () => {
    if (!cardRef.current) return;
    
    try {
      setIsExporting(true);
      
      const dataUrl = await toPng(cardRef.current, {
        width: CONFIG.exportWidth,
        height: CONFIG.exportHeight,
        pixelRatio: 2,
        backgroundColor: '#1a1a2e',
      });
      
      // Téléchargement
      const link = document.createElement('a');
      link.download = `yotoshare-${playlist.title.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Erreur export:', err);
      alert('Erreur lors de l\'export. Essayez de faire un screenshot manuel.');
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white">Chargement de la playlist...</p>
        </div>
      </div>
    );
  }

  if (error || !playlist) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800/50 rounded-2xl p-8 text-center max-w-md">
          <p className="text-red-400 mb-4">{error || 'Playlist introuvable'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all"
          >
            Retour au dashboard
          </button>
        </div>
      </div>
    );
  }

  const tracks = extractAllTracks(playlist);
  const totalDuration = calculateTotalDuration(playlist);
  const coverUrl = playlist.metadata?.cover?.imageL || playlist.metadata?.cover?.imageM || playlist.metadata?.cover?.imageS;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Retour</span>
          </button>
          
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-6 py-2.5 bg-gradient-to-r from-orange-500 to-orange-400 text-white font-semibold rounded-xl hover:from-orange-600 hover:to-orange-500 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {isExporting ? (
              <>
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Export...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Télécharger PNG</span>
              </>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex flex-col xl:flex-row gap-8">
          {/* Panneau de contrôle */}
          <div className="w-full xl:w-80 shrink-0">
            <div className="bg-slate-800/50 rounded-2xl p-6 sticky top-24">
              <h2 className="text-white font-semibold text-lg mb-6 flex items-center gap-2">
                <span>🎨</span> Personnalisation
              </h2>

              {/* Sélecteur de couleur */}
              <div className="mb-6">
                <label className="block text-slate-400 text-sm mb-3">Couleur d'accent</label>
                <div className="grid grid-cols-3 gap-3">
                  {COLOR_PRESETS.map((preset) => (
                    <button
                      key={preset.color}
                      onClick={() => setAccentColor(preset.color)}
                      className={`aspect-square rounded-xl transition-all ${
                        accentColor === preset.color
                          ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-105'
                          : 'hover:scale-105'
                      }`}
                      style={{ background: preset.bg }}
                      title={preset.name}
                    />
                  ))}
                </div>
              </div>

              {/* Info playlist */}
              <div className="border-t border-slate-700 pt-6">
                <h3 className="text-white font-medium mb-3">{playlist.title}</h3>
                <div className="space-y-2 text-sm text-slate-400">
                  <p>🎵 {tracks.length} pistes</p>
                  <p>⏱️ {formatDuration(totalDuration)}</p>
                </div>
              </div>

              {/* Tips */}
              <div className="mt-6 p-4 bg-orange-500/10 rounded-xl border border-orange-500/20">
                <p className="text-orange-400 text-sm">
                  💡 Le visuel est optimisé pour Facebook (940×788px)
                </p>
              </div>
            </div>
          </div>

          {/* Preview de la carte */}
          <div className="flex-1 flex justify-center">
            <div className="overflow-auto">
              <CardPreview
                ref={cardRef}
                playlist={playlist}
                tracks={tracks}
                totalDuration={totalDuration}
                coverUrl={coverUrl}
                accentColor={accentColor}
                selectedPreset={selectedPreset}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// Composant de la carte (séparé pour le ref)
import { forwardRef } from 'react';

const CardPreview = forwardRef(function CardPreview(
  { playlist, tracks, totalDuration, coverUrl, accentColor, selectedPreset },
  ref
) {
  return (
    <div
      ref={ref}
      className="relative overflow-hidden"
      style={{
        width: CONFIG.exportWidth,
        height: CONFIG.exportHeight,
        borderRadius: 30,
        fontFamily: '"Nunito", "Segoe UI", system-ui, sans-serif',
      }}
    >
      {/* Background */}
      <div
        className="absolute inset-0"
        style={{ background: selectedPreset.bg }}
      />
      
      {/* Pattern décoratif */}
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `
            radial-gradient(circle at 20% 80%, white 2px, transparent 2px),
            radial-gradient(circle at 80% 20%, white 3px, transparent 3px),
            radial-gradient(circle at 40% 40%, white 1.5px, transparent 1.5px)
          `,
          backgroundSize: '100px 100px, 150px 150px, 80px 80px',
        }}
      />

      {/* Contenu */}
      <div className="relative h-full flex p-10 gap-10">
        {/* Colonne gauche */}
        <div className="flex flex-col items-center w-64">
          {/* Cover - format portrait 2:3 comme les cartes Yoto */}
          <div
            className="w-52 rounded-3xl overflow-hidden bg-black flex items-center justify-center"
            style={{
              aspectRatio: '2/3',
              boxShadow: '0 20px 60px rgba(0,0,0,0.4), 0 0 0 6px rgba(255,255,255,0.2)',
            }}
          >
            {coverUrl ? (
              <img src={coverUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="text-6xl">🎵</span>
            )}
          </div>

          {/* Signature */}
          <div
            className="mt-auto px-6 py-3 rounded-2xl"
            style={{
              background: 'rgba(0,0,0,0.3)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <span className="text-white font-semibold">{CONFIG.signature}</span>
          </div>
        </div>

        {/* Colonne droite */}
        <div className="flex-1 flex flex-col">
          {/* Titre */}
          <h1
            className="text-white font-extrabold leading-tight mb-3"
            style={{
              fontSize: 48,
              textShadow: '0 4px 20px rgba(0,0,0,0.3)',
              fontFamily: '"Fredoka One", "Nunito", system-ui, sans-serif',
            }}
          >
            {playlist.title}
          </h1>

          {/* Meta tags */}
          <div className="flex gap-4 mb-6">
            <div
              className="px-5 py-2.5 rounded-full flex items-center gap-2 text-white font-semibold"
              style={{
                background: 'rgba(255,255,255,0.2)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <span>🎵</span>
              <span>{tracks.length} pistes</span>
            </div>
            <div
              className="px-5 py-2.5 rounded-full flex items-center gap-2 text-white font-semibold"
              style={{
                background: 'rgba(255,255,255,0.2)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <span>⏱️</span>
              <span>{formatDuration(totalDuration)}</span>
            </div>
          </div>

          {/* Liste des pistes */}
          <div
            className="flex-1 rounded-3xl p-6 overflow-hidden"
            style={{
              background: 'rgba(255,255,255,0.95)',
              boxShadow: '0 15px 50px rgba(0,0,0,0.2)',
            }}
          >
            <div
              className="font-extrabold text-slate-800 text-xl mb-4 flex items-center gap-2"
              style={{ fontFamily: '"Fredoka One", system-ui' }}
            >
              <span>📋</span>
              <span>Liste des pistes</span>
            </div>

            <div className="space-y-2">
              {tracks.slice(0, 8).map((track, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl"
                  style={{ background: i % 2 === 0 ? '#f8f9fa' : '#f1f3f4' }}
                >
                  {/* Icône de la piste */}
                  <span
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 overflow-hidden"
                    style={{ background: track.icon ? 'transparent' : accentColor }}
                  >
                    {track.icon ? (
                      <img src={track.icon} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                      </svg>
                    )}
                  </span>
                  {/* Titre */}
                  <span className="font-semibold text-slate-800 truncate flex-1">
                    {track.title}
                  </span>
                  {/* Durée */}
                  <span className="text-slate-500 text-sm font-medium shrink-0">
                    {formatTrackDuration(track.duration)}
                  </span>
                </div>
              ))}

              {tracks.length > 8 && (
                <div
                  className="flex items-center justify-center px-4 py-2.5 rounded-xl text-slate-500 font-medium"
                  style={{ background: '#f1f3f4' }}
                >
                  + {tracks.length - 8} autres pistes...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});
