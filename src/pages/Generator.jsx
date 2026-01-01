import { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { toPng } from 'html-to-image';
import { Vibrant } from 'node-vibrant/browser';
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
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [accentColor, setAccentColor] = useState(COLOR_PRESETS[0].color);
  const [customColor, setCustomColor] = useState('#F95E3F');
  const [extractedColors, setExtractedColors] = useState(null);
  const [error, setError] = useState(null);

  // État des métadonnées
  const [category, setCategory] = useState('none');
  const [genre, setGenre] = useState('');
  const [languages, setLanguages] = useState([]);
  const [sources, setSources] = useState([]);
  const [tags, setTags] = useState('');

  const CATEGORIES = [
    { value: 'none', label: 'Aucune' },
    { value: 'stories', label: 'Histoires' },
    { value: 'music', label: 'Musique' },
    { value: 'radio', label: 'Radio' },
    { value: 'podcast', label: 'Podcast' },
    { value: 'sfx', label: 'Effets sonores' },
    { value: 'activities', label: 'Activités' },
    { value: 'alarms', label: 'Alarmes' },
  ];

  const LANGUAGES = [
    { value: 'fr', label: 'Français', flag: 'fr' },
    { value: 'fr-fr', label: 'Français (France)', flag: 'fr' },
    { value: 'en', label: 'Anglais', flag: 'gb' },
    { value: 'en-gb', label: 'Anglais (UK)', flag: 'gb' },
    { value: 'en-us', label: 'Anglais (US)', flag: 'us' },
    { value: 'de', label: 'Allemand', flag: 'de' },
    { value: 'es', label: 'Espagnol', flag: 'es' },
    { value: 'it', label: 'Italien', flag: 'it' },
  ];

  // URL des drapeaux (flagcdn.com)
  const getFlagUrl = (code) => `https://flagcdn.com/24x18/${code}.png`;

  const SOURCES = [
    { value: 'youtube', label: 'YouTube', icon: '▶️', tag: 'YouTube' },
    { value: 'tonie', label: 'Tonie', icon: '🎧', tag: 'Tonie' },
    { value: 'yoto', label: 'Yoto', icon: '🟠', tag: 'Yoto' },
    { value: 'spotify', label: 'Spotify', icon: '🎵', tag: 'Spotify' },
    { value: 'podcast', label: 'Podcast', icon: '🎙️', tag: 'Podcast' },
  ];

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
        // Initialise les métadonnées depuis la playlist
        if (data.metadata) {
          setCategory(data.metadata.category || 'none');
          setGenre(Array.isArray(data.metadata.genre) ? data.metadata.genre.join(', ') : '');
          setLanguages(Array.isArray(data.metadata.languages) ? data.metadata.languages : []);
          setTags(Array.isArray(data.metadata.tags) ? data.metadata.tags.join(', ') : '');
        }
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

  // Extraire les couleurs de la cover
  useEffect(() => {
    const extractColors = async () => {
      const coverUrl = playlist?.metadata?.cover?.imageL || playlist?.metadata?.cover?.imageM;
      if (!coverUrl) return;

      try {
        const palette = await Vibrant.from(coverUrl).getPalette();
        const colors = {};

        if (palette.Vibrant) {
          colors.vibrant = palette.Vibrant.hex;
        }
        if (palette.Muted) {
          colors.muted = palette.Muted.hex;
        }
        if (palette.DarkVibrant) {
          colors.darkVibrant = palette.DarkVibrant.hex;
        }
        if (palette.LightVibrant) {
          colors.lightVibrant = palette.LightVibrant.hex;
        }
        if (palette.DarkMuted) {
          colors.darkMuted = palette.DarkMuted.hex;
        }
        if (palette.LightMuted) {
          colors.lightMuted = palette.LightMuted.hex;
        }

        setExtractedColors(colors);
        // Sélectionne automatiquement la couleur Vibrant si disponible
        if (colors.vibrant) {
          setAccentColor(colors.vibrant);
        }
      } catch (err) {
        console.error('Erreur extraction couleurs:', err);
      }
    };

    if (playlist) {
      extractColors();
    }
  }, [playlist]);

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

  const handleSaveMetadata = async () => {
    try {
      setIsSaving(true);
      setSaveSuccess(false);
      const token = await getValidToken();

      // Combine les tags manuels avec les tags des sources
      const manualTags = tags.split(',').map(t => t.trim()).filter(Boolean);
      const sourceTags = sources.map(s => SOURCES.find(src => src.value === s)?.tag).filter(Boolean);
      const allTags = [...new Set([...sourceTags, ...manualTags])];

      // Envoie la playlist complète avec les métadonnées mises à jour
      const updatedPlaylist = {
        title: playlist.title,
        content: playlist.content,
        metadata: {
          ...playlist.metadata,
          category,
          genre: genre.split(',').map(g => g.trim()).filter(Boolean),
          languages,
          tags: allTags,
        },
      };

      await yotoAPI.updateContent(token, cardId, updatedPlaylist);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Erreur sauvegarde:', err);
      alert('Erreur lors de la sauvegarde des métadonnées');
    } finally {
      setIsSaving(false);
    }
  };

  const toggleLanguage = (lang) => {
    setLanguages(prev =>
      prev.includes(lang)
        ? prev.filter(l => l !== lang)
        : [...prev, lang]
    );
  };

  const toggleSource = (source) => {
    setSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  // Combine les tags manuels avec les tags des sources
  const getAllTags = () => {
    const manualTags = tags.split(',').map(t => t.trim()).filter(Boolean);
    const sourceTags = sources.map(s => SOURCES.find(src => src.value === s)?.tag).filter(Boolean);
    return [...new Set([...sourceTags, ...manualTags])];
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
            <div className="bg-slate-800/50 rounded-2xl p-6">
              <h2 className="text-white font-semibold text-lg mb-6 flex items-center gap-2">
                <span>🎨</span> Personnalisation
              </h2>

              {/* Couleurs extraites de la cover */}
              {extractedColors && Object.keys(extractedColors).length > 0 && (
                <div className="mb-6">
                  <label className="block text-slate-400 text-sm mb-3">Couleurs de la cover</label>
                  <div className="grid grid-cols-6 gap-2">
                    {extractedColors.vibrant && (
                      <button
                        onClick={() => setAccentColor(extractedColors.vibrant)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.vibrant
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.vibrant }}
                        title="Vibrant"
                      />
                    )}
                    {extractedColors.lightVibrant && (
                      <button
                        onClick={() => setAccentColor(extractedColors.lightVibrant)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.lightVibrant
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.lightVibrant }}
                        title="Light Vibrant"
                      />
                    )}
                    {extractedColors.darkVibrant && (
                      <button
                        onClick={() => setAccentColor(extractedColors.darkVibrant)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.darkVibrant
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.darkVibrant }}
                        title="Dark Vibrant"
                      />
                    )}
                    {extractedColors.muted && (
                      <button
                        onClick={() => setAccentColor(extractedColors.muted)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.muted
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.muted }}
                        title="Muted"
                      />
                    )}
                    {extractedColors.lightMuted && (
                      <button
                        onClick={() => setAccentColor(extractedColors.lightMuted)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.lightMuted
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.lightMuted }}
                        title="Light Muted"
                      />
                    )}
                    {extractedColors.darkMuted && (
                      <button
                        onClick={() => setAccentColor(extractedColors.darkMuted)}
                        className={`aspect-square rounded-lg transition-all ${
                          accentColor === extractedColors.darkMuted
                            ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                            : 'hover:scale-110'
                        }`}
                        style={{ background: extractedColors.darkMuted }}
                        title="Dark Muted"
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Color picker personnalisé */}
              <div className="mb-6">
                <label className="block text-slate-400 text-sm mb-3">Couleur personnalisée</label>
                <div className="flex gap-3">
                  <input
                    type="color"
                    value={customColor}
                    onChange={(e) => {
                      setCustomColor(e.target.value);
                      setAccentColor(e.target.value);
                    }}
                    className="w-12 h-12 rounded-xl cursor-pointer border-0 bg-transparent"
                  />
                  <button
                    onClick={() => setAccentColor(customColor)}
                    className={`flex-1 rounded-xl transition-all flex items-center justify-center ${
                      accentColor === customColor
                        ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800'
                        : 'hover:scale-[1.02]'
                    }`}
                    style={{ background: customColor }}
                  >
                    <span className="text-white text-sm font-medium drop-shadow">{customColor}</span>
                  </button>
                </div>
              </div>

              {/* Presets */}
              <div className="mb-6">
                <label className="block text-slate-400 text-sm mb-3">Presets</label>
                <div className="grid grid-cols-6 gap-2">
                  {COLOR_PRESETS.map((preset) => (
                    <button
                      key={preset.color}
                      onClick={() => setAccentColor(preset.color)}
                      className={`aspect-square rounded-lg transition-all ${
                        accentColor === preset.color
                          ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800 scale-110'
                          : 'hover:scale-110'
                      }`}
                      style={{ background: preset.color }}
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

            {/* Métadonnées */}
            <div className="bg-slate-800/50 rounded-2xl p-6 mt-6">
              <h2 className="text-white font-semibold text-lg mb-6 flex items-center gap-2">
                <span>📝</span> Métadonnées
              </h2>

              {/* Catégorie */}
              <div className="mb-4">
                <label className="block text-slate-400 text-sm mb-2">Catégorie</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-orange-500"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>

              {/* Genre */}
              <div className="mb-4">
                <label className="block text-slate-400 text-sm mb-2">Genre (séparés par virgule)</label>
                <input
                  type="text"
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  placeholder="Aventure, Fantaisie..."
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
                />
              </div>

              {/* Langues */}
              <div className="mb-4">
                <label className="block text-slate-400 text-sm mb-2">Langues</label>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGES.map(lang => (
                    <button
                      key={lang.value}
                      type="button"
                      onClick={() => toggleLanguage(lang.value)}
                      className={`px-3 py-1 rounded-full text-sm transition-all ${
                        languages.includes(lang.value)
                          ? 'bg-orange-500 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Sources */}
              <div className="mb-4">
                <label className="block text-slate-400 text-sm mb-2">Source</label>
                <div className="flex flex-wrap gap-2">
                  {SOURCES.map(source => (
                    <button
                      key={source.value}
                      type="button"
                      onClick={() => toggleSource(source.value)}
                      className={`px-3 py-1 rounded-full text-sm transition-all flex items-center gap-1 ${
                        sources.includes(source.value)
                          ? 'bg-orange-500 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      <span>{source.icon}</span>
                      <span>{source.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Tags */}
              <div className="mb-6">
                <label className="block text-slate-400 text-sm mb-2">Tags additionnels (séparés par virgule)</label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="histoire, enfants, audio..."
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
                />
                {sources.length > 0 && (
                  <p className="text-slate-500 text-xs mt-1">
                    Tags auto: {sources.map(s => SOURCES.find(src => src.value === s)?.tag).filter(Boolean).join(', ')}
                  </p>
                )}
              </div>

              {/* Bouton sauvegarder */}
              <button
                onClick={handleSaveMetadata}
                disabled={isSaving}
                className={`w-full py-2.5 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 ${
                  saveSuccess
                    ? 'bg-green-500 text-white'
                    : 'bg-orange-500 hover:bg-orange-600 text-white disabled:opacity-50'
                }`}
              >
                {isSaving ? (
                  <>
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Sauvegarde...</span>
                  </>
                ) : saveSuccess ? (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Sauvegardé !</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                    </svg>
                    <span>Sauvegarder</span>
                  </>
                )}
              </button>
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
                category={category}
                genre={genre}
                languages={languages}
                sources={sources}
                tags={getAllTags()}
                CATEGORIES={CATEGORIES}
                LANGUAGES={LANGUAGES}
                SOURCES={SOURCES}
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

// Génère un dégradé à partir d'une couleur
function generateGradient(hexColor) {
  // Convertit hex en RGB
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);

  // Crée une version plus claire pour le dégradé
  const lighterR = Math.min(255, r + 60);
  const lighterG = Math.min(255, g + 60);
  const lighterB = Math.min(255, b + 60);
  const lighterHex = `#${lighterR.toString(16).padStart(2, '0')}${lighterG.toString(16).padStart(2, '0')}${lighterB.toString(16).padStart(2, '0')}`;

  return `linear-gradient(135deg, ${hexColor} 0%, ${lighterHex} 100%)`;
}

const CardPreview = forwardRef(function CardPreview(
  { playlist, tracks, totalDuration, coverUrl, accentColor, selectedPreset, category, genre, languages, sources, tags, CATEGORIES, LANGUAGES, SOURCES },
  ref
) {
  // Génère le fond : utilise le preset si la couleur correspond, sinon génère un dégradé
  const backgroundStyle = selectedPreset?.color === accentColor
    ? selectedPreset.bg
    : generateGradient(accentColor);

  // Prépare les métadonnées à afficher
  const categoryLabel = category && category !== 'none'
    ? CATEGORIES.find(c => c.value === category)?.label
    : null;
  const genreArray = genre ? genre.split(',').map(g => g.trim()).filter(Boolean) : [];
  const languageData = languages.length > 0
    ? languages.map(l => LANGUAGES.find(lang => lang.value === l)).filter(Boolean)
    : [];
  const sourceData = sources?.length > 0
    ? sources.map(s => SOURCES.find(src => src.value === s)).filter(Boolean)
    : [];
  // tags est déjà un tableau
  const tagsArray = Array.isArray(tags) ? tags : [];
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
        style={{ background: backgroundStyle }}
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
      <div className="relative h-full flex p-10 gap-8">
        {/* Colonne gauche */}
        <div className="flex flex-col items-center w-80">
          {/* Cover - format portrait 2:3 comme les cartes Yoto */}
          <div
            className="w-64 rounded-3xl overflow-hidden bg-black flex items-center justify-center"
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

          {/* Métadonnées */}
          {(categoryLabel || languageData.length > 0 || sourceData.length > 0 || genreArray.length > 0 || tagsArray.length > 0) && (
            <div className="mt-4 flex flex-col gap-2">
              {/* Catégorie, Langue et Source */}
              {(categoryLabel || languageData.length > 0 || sourceData.length > 0) && (
                <div className="flex flex-wrap gap-2 justify-center">
                  {categoryLabel && (
                    <span
                      className="px-3 py-1.5 rounded-full text-white text-xs font-medium flex items-center gap-1"
                      style={{ background: 'rgba(255,255,255,0.2)' }}
                    >
                      📁 {categoryLabel}
                    </span>
                  )}
                  {languageData.length > 0 && (
                    <span
                      className="px-3 py-1.5 rounded-full text-white text-xs font-medium flex items-center gap-1.5"
                      style={{ background: 'rgba(255,255,255,0.2)' }}
                    >
                      {languageData.map((l, i) => (
                        <img
                          key={i}
                          src={`https://flagcdn.com/24x18/${l.flag}.png`}
                          alt={l.label}
                          className="h-3 inline-block"
                          style={{ verticalAlign: 'middle' }}
                        />
                      ))}
                      <span>{languageData.map(l => l.label).join(', ')}</span>
                    </span>
                  )}
                  {sourceData.length > 0 && (
                    <span
                      className="px-3 py-1.5 rounded-full text-white text-xs font-medium flex items-center gap-1"
                      style={{ background: 'rgba(255,255,255,0.2)' }}
                    >
                      📀 {sourceData.map(s => s.label).join(', ')}
                    </span>
                  )}
                </div>
              )}
              {/* Genre et Tags */}
              {(genreArray.length > 0 || tagsArray.length > 0) && (
                <div className="flex flex-wrap gap-1.5 justify-center">
                  {genreArray.map((g, i) => (
                    <span
                      key={`genre-${i}`}
                      className="px-2.5 py-1 rounded-full text-white text-xs font-medium"
                      style={{ background: accentColor }}
                    >
                      {g}
                    </span>
                  ))}
                  {tagsArray.map((t, i) => (
                    <span
                      key={`tag-${i}`}
                      className="px-2.5 py-1 rounded-full text-white text-xs font-medium"
                      style={{ background: 'rgba(255,255,255,0.25)' }}
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

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

          {/* Meta tags - pistes et durée uniquement */}
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
              className="font-bold text-slate-800 text-xl mb-4 flex items-center gap-2"
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
