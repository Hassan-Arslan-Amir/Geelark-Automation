import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { BotSettings } from '../types';

const SETTINGS_ROW_ID = 1;

const emptySettings: BotSettings = {
  google_drive_url: '',
  openai_api_key: '',
  geelark_app_id: '',
  geelark_api_key: '',
  geelark_bearer_token: '',
};

export function useBotSettings() {
  const [settings, setSettings] = useState<BotSettings>(emptySettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    if (!supabase) {
      setError('Supabase is not configured.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { data, error: fetchError } = await supabase
        .from('bot_settings')
        .select('google_drive_url, openai_api_key, geelark_app_id, geelark_api_key, geelark_bearer_token')
        .eq('id', SETTINGS_ROW_ID)
        .maybeSingle();

      if (fetchError) throw fetchError;

      if (data) {
        setSettings({
          google_drive_url: data.google_drive_url ?? '',
          openai_api_key: data.openai_api_key ?? '',
          geelark_app_id: data.geelark_app_id ?? '',
          geelark_api_key: data.geelark_api_key ?? '',
          geelark_bearer_token: data.geelark_bearer_token ?? '',
        });
      } else {
        setSettings(emptySettings);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load settings.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const saveSettings = async (next: BotSettings): Promise<void> => {
    if (!supabase) {
      throw new Error('Supabase is not configured.');
    }

    setSaving(true);
    setError(null);

    try {
      const { error: upsertError } = await supabase.from('bot_settings').upsert(
        {
          id: SETTINGS_ROW_ID,
          google_drive_url: next.google_drive_url.trim() || null,
          openai_api_key: next.openai_api_key.trim() || null,
          geelark_app_id: next.geelark_app_id.trim() || null,
          geelark_api_key: next.geelark_api_key.trim() || null,
          geelark_bearer_token: next.geelark_bearer_token.trim() || null,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'id' },
      );

      if (upsertError) throw upsertError;
      setSettings(next);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save settings.';
      setError(message);
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const clearError = useCallback(() => setError(null), []);

  return { settings, loading, saving, error, saveSettings, refetch: fetchSettings, clearError };
}
