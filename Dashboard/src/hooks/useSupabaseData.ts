import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { AnalyticsData, Account } from '../types';

/** Extract a readable message from anything the Supabase client may throw. */
function extractMessage(err: unknown): string {
  if (err && typeof err === 'object') {
    const e = err as Record<string, unknown>;
    if (typeof e.message === 'string') return e.message;
    if (typeof e.error_description === 'string') return e.error_description;
  }
  if (err instanceof Error) return err.message;
  return 'Unknown error — check the browser console for details.';
}

export function useSupabaseData() {
  const [data, setData]       = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      // Guard: env vars not configured yet
      if (!supabase) {
        setError(
          'Supabase credentials are missing.\n' +
          'Create Dashboard/.env with:\n' +
          '  VITE_SUPABASE_URL=https://your-project.supabase.co\n' +
          '  VITE_SUPABASE_ANON_KEY=your-anon-public-key'
        );
        setLoading(false);
        return;
      }

      try {
        // ── 1. Fetch all devices that have a username ──────────────────────
        const { data: devices, error: devicesError } = await supabase
          .from('devices')
          .select('id, mobile, profile_id, username')
          .not('username', 'is', null);

        if (devicesError) throw devicesError;

        // ── 2. Fetch all post stats ────────────────────────────────────────
        const { data: stats, error: statsError } = await supabase
          .from('stats')
          .select('device_id, permalink, media_type, views, likes, comments, reshares, reach, impressions, saves, posted_at');

        if (statsError) throw statsError;

        // ── 3. Group stats rows by device_id ──────────────────────────────
        type StatRow = NonNullable<typeof stats>[number];
        const statsByDevice: Record<number, StatRow[]> = {};
        for (const stat of stats ?? []) {
          if (!statsByDevice[stat.device_id]) statsByDevice[stat.device_id] = [];
          statsByDevice[stat.device_id].push(stat);
        }

        // ── 4. Assemble Account[] (same shape the components already expect)
        const accounts: Account[] = (devices ?? []).map((device) => ({
          profile_id: device.profile_id,
          mobile:     device.mobile,
          username:   device.username,
          posts: (statsByDevice[device.id] ?? []).map((stat) => ({
            permalink: stat.permalink,
            stats: {
              views:       stat.views       ?? 0,
              likes:       stat.likes       ?? 0,
              comments:    stat.comments    ?? 0,
              reshares:    stat.reshares    ?? 0,
              media_type:  stat.media_type  ?? 0,
              // posted_at is an ISO string in DB; components expect a Unix timestamp
              timestamp:   stat.posted_at
                ? Math.floor(new Date(stat.posted_at).getTime() / 1000)
                : 0,
              reach:       stat.reach       ?? 0,
              impressions: stat.impressions ?? 0,
              saves:       stat.saves       ?? 0,
            },
          })),
        }));

        console.log(`[useSupabaseData] loaded ${accounts.length} devices, ${stats?.length ?? 0} stat rows`);

        // ── 5. Compute top-level aggregates ───────────────────────────────
        const totalViews    = accounts.reduce((s, a) => s + a.posts.reduce((ps, p) => ps + p.stats.views,    0), 0);
        const totalLikes    = accounts.reduce((s, a) => s + a.posts.reduce((ps, p) => ps + p.stats.likes,    0), 0);
        const totalComments = accounts.reduce((s, a) => s + a.posts.reduce((ps, p) => ps + p.stats.comments, 0), 0);

        setData({
          fetched_at:    new Date().toISOString(),
          total_devices: accounts.length,
          aggregate: {
            total_views:    totalViews,
            total_likes:    totalLikes,
            total_comments: totalComments,
          },
          accounts,
        });
      } catch (err: unknown) {
        const message = extractMessage(err);
        console.error('[useSupabaseData] fetch failed:', err);
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  return { data, loading, error };
}
