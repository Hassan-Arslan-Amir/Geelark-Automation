import { supabase } from '../lib/supabase';
import { ScheduledPostPayload } from '../types';

export async function schedulePost(payload: ScheduledPostPayload): Promise<void> {
  if (!supabase) {
    throw new Error('Supabase is not configured.');
  }

  const { error } = await supabase.from('scheduled_posts').insert({
    platform: payload.platform,
    media_type: payload.media_type,
    resource_url: payload.resource_url,
    caption: payload.caption || null,
    device_ids: payload.device_ids,
    schedule_at: payload.schedule_at,
    status: 'pending',
  });

  if (error) throw error;
}
