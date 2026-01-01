import { CONFIG } from '../config';
import useAuth from '../hooks/useAuth';

export default function Home() {
  const { login, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo et titre */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-gradient-to-br from-orange-500 to-orange-400 shadow-2xl shadow-orange-500/30 mb-6">
            <svg viewBox="0 0 60 60" className="w-14 h-14">
              <rect x="12" y="10" width="30" height="36" rx="4" fill="white" />
              <circle cx="27" cy="18" r="3" fill="#F95E3F" opacity="0.5" />
              {/* Y en pixel */}
              <rect x="17" y="24" width="4" height="4" fill="#F95E3F" />
              <rect x="33" y="24" width="4" height="4" fill="#F95E3F" />
              <rect x="21" y="28" width="4" height="4" fill="#F95E3F" />
              <rect x="29" y="28" width="4" height="4" fill="#F95E3F" />
              <rect x="25" y="32" width="4" height="12" fill="#F95E3F" />
              {/* Share icon */}
              <circle cx="42" cy="40" r="10" fill="#F95E3F" />
              <path d="M38 42 L42 36 L46 42" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
              <line x1="42" y1="37" x2="42" y2="46" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          
          <h1 className="text-4xl font-bold text-white mb-2" style={{ fontFamily: 'system-ui' }}>
            {CONFIG.appName}
          </h1>
          <p className="text-slate-400 text-lg">
            Créez de jolis visuels pour partager vos playlists Yoto
          </p>
        </div>

        {/* Card de connexion */}
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-3xl p-8 shadow-2xl border border-slate-700/50">
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-white mb-2">
                Connectez-vous avec Yoto
              </h2>
              <p className="text-slate-400 text-sm">
                Accédez à vos playlists MYO et générez des visuels en quelques clics
              </p>
            </div>

            <button
              onClick={login}
              disabled={isLoading}
              className="w-full py-4 px-6 bg-gradient-to-r from-orange-500 to-orange-400 hover:from-orange-600 hover:to-orange-500 text-white font-semibold rounded-2xl transition-all duration-200 transform hover:scale-[1.02] hover:shadow-lg hover:shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Chargement...</span>
                </>
              ) : (
                <>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
                  <span>Se connecter avec Yoto</span>
                </>
              )}
            </button>

            <div className="flex items-center gap-4 text-slate-500 text-sm">
              <div className="flex-1 h-px bg-slate-700" />
              <span>Sécurisé par OAuth</span>
              <div className="flex-1 h-px bg-slate-700" />
            </div>

            {/* Features */}
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <span className="text-green-400">✓</span>
                <span>Accès à vos MYO</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <span className="text-green-400">✓</span>
                <span>Export PNG</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <span className="text-green-400">✓</span>
                <span>Templates stylés</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <span className="text-green-400">✓</span>
                <span>100% gratuit</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-500 text-sm mt-6">
          Créé avec ❤️ par Mathieu
        </p>
      </div>
    </div>
  );
}
