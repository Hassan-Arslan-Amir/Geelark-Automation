import { useEffect, useState } from 'react';
import { Cloud, Eye, EyeOff, FolderOpen, Loader2, Save, Settings } from 'lucide-react';
import { FieldHelp } from './FieldHelp';
import { useBotSettings } from '../hooks/useBotSettings';
import { useAutoDismiss } from '../hooks/useAutoDismiss';

const inputClass =
  'w-full px-4 py-3 border border-surface-200 rounded-xl bg-surface-0 text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 transition-all text-sm';

const GEELARK_HELP = {
  appId:
    'Sign in to the GeeLark dashboard, open Settings → API / Open API, and copy the App ID (appId) shown for your application.',
  apiKey:
    'On the same GeeLark API settings page, copy the API Key. The bot uses it to sign each Open API request (phone list, posting tasks, etc.).',
  bearerToken:
    'Find this under GeeLark API or upload settings. It is used as a Bearer token when uploading media files to GeeLark storage before posting to devices.',
} as const;

function SecretInput({
  id,
  label,
  help,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  help: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <label htmlFor={id} className="flex items-center text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
        {label}
        <FieldHelp text={help} />
      </label>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${inputClass} pr-12 font-mono`}
          autoComplete="off"
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-surface-400 hover:text-surface-600 hover:bg-surface-100 transition-colors"
          aria-label={visible ? `Hide ${label}` : `Show ${label}`}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    </div>
  );
}

export function SettingsScreen() {
  const { settings, loading, saving, error, saveSettings, clearError } = useBotSettings();

  const [googleDriveUrl, setGoogleDriveUrl] = useState('');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [geelarkAppId, setGeelarkAppId] = useState('');
  const [geelarkApiKey, setGeelarkApiKey] = useState('');
  const [geelarkBearerToken, setGeelarkBearerToken] = useState('');
  const [showOpenAiKey, setShowOpenAiKey] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    if (!loading) {
      setGoogleDriveUrl(settings.google_drive_url);
      setOpenaiApiKey(settings.openai_api_key);
      setGeelarkAppId(settings.geelark_app_id);
      setGeelarkApiKey(settings.geelark_api_key);
      setGeelarkBearerToken(settings.geelark_bearer_token);
    }
  }, [loading, settings]);

  useAutoDismiss(feedback, () => setFeedback(null));
  useAutoDismiss(error, clearError);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    try {
      await saveSettings({
        google_drive_url: googleDriveUrl,
        openai_api_key: openaiApiKey,
        geelark_app_id: geelarkAppId,
        geelark_api_key: geelarkApiKey,
        geelark_bearer_token: geelarkBearerToken,
      });
      setFeedback({ type: 'success', message: 'Settings saved successfully.' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save settings.';
      setFeedback({ type: 'error', message });
    }
  };

  if (loading) {
    return (
      <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-surface-500 text-sm font-medium">Loading settings…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Settings</h1>
          <p className="text-surface-500 mt-1 text-sm">
            Configure GeeLark connectivity, content source, and OpenAI for the automation bot.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
          <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
            <div className="flex items-center gap-2 mb-5">
              <Cloud size={18} className="text-brand-600" />
              <h2 className="text-base font-bold text-surface-900">GeeLark connectivity</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="geelarkAppId" className="flex items-center text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                  GeeLark App ID
                  <FieldHelp text={GEELARK_HELP.appId} />
                </label>
                <input
                  id="geelarkAppId"
                  type="text"
                  placeholder="Your GeeLark App ID"
                  value={geelarkAppId}
                  onChange={(e) => setGeelarkAppId(e.target.value)}
                  className={`${inputClass} font-mono`}
                  autoComplete="off"
                />
              </div>

              <SecretInput
                id="geelarkApiKey"
                label="GeeLark API key"
                help={GEELARK_HELP.apiKey}
                value={geelarkApiKey}
                onChange={setGeelarkApiKey}
                placeholder="Your GeeLark API key"
              />

              <SecretInput
                id="geelarkBearerToken"
                label="GeeLark Bearer token"
                help={GEELARK_HELP.bearerToken}
                value={geelarkBearerToken}
                onChange={setGeelarkBearerToken}
                placeholder="Bearer token for media uploads"
              />
            </div>
          </div>

          <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
            <div className="flex items-center gap-2 mb-5">
              <FolderOpen size={18} className="text-brand-600" />
              <h2 className="text-base font-bold text-surface-900">Content source</h2>
            </div>

            <div>
              <label htmlFor="googleDriveUrl" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                Google Drive link
              </label>
              <input
                id="googleDriveUrl"
                type="url"
                placeholder="https://drive.google.com/drive/folders/..."
                value={googleDriveUrl}
                onChange={(e) => setGoogleDriveUrl(e.target.value)}
                className={inputClass}
              />
              <p className="text-xs text-surface-400 mt-2">
                The bot will connect to this folder to download content for posting.
              </p>
            </div>
          </div>

          <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
            <div className="mb-5">
              <h2 className="text-base font-bold text-surface-900">OpenAI API key</h2>
              <p className="text-sm text-surface-500 mt-0.5">
                Required when caption generation is enabled on a task. The prompt is configured per task in Schedule Post.
              </p>
            </div>

            <div>
              <label htmlFor="openaiApiKey" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                API key
              </label>
              <div className="relative">
                <input
                  id="openaiApiKey"
                  type={showOpenAiKey ? 'text' : 'password'}
                  placeholder="sk-..."
                  value={openaiApiKey}
                  onChange={(e) => setOpenaiApiKey(e.target.value)}
                  className={`${inputClass} pr-12 font-mono`}
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowOpenAiKey((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-surface-400 hover:text-surface-600 hover:bg-surface-100 transition-colors"
                  aria-label={showOpenAiKey ? 'Hide API key' : 'Show API key'}
                >
                  {showOpenAiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
          </div>

          {(error || feedback) && (
            <div
              className={`rounded-xl px-4 py-3 text-sm font-medium ${
                feedback?.type === 'success'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-red-50 text-red-700 border border-red-200'
              }`}
            >
              {feedback?.message ?? error}
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-brand-600/25 transition-colors"
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving…
              </>
            ) : (
              <>
                <Save size={16} />
                Save settings
              </>
            )}
          </button>
        </form>

        <div className="max-w-3xl mt-8 flex items-start gap-3 px-4 py-3 rounded-xl bg-surface-100/80 border border-surface-200/60">
          <Settings size={16} className="text-surface-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-surface-500 leading-relaxed">
            Hover the <span className="font-semibold">?</span> next to each GeeLark field for instructions on where to find the value in your GeeLark account.
          </p>
        </div>
      </div>
    </div>
  );
}
