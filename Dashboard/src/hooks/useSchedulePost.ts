import { supabase } from '../lib/supabase';
import {
  ScheduleConflictError,
  expandTimesForDuration,
  findInternalScheduleConflict,
  findPendingScheduleConflict,
  formatScheduleTimeDisplay,
  generateAutoScheduleTimes,
  getDurationDayCount,
  getTaskScheduleTimes,
  MIN_TASK_GAP_MINUTES,
  normalizeScheduleMinute,
  resolveAllScheduleConflicts,
} from '../lib/scheduleTimes';
import { ScheduleDuration, ScheduledTask, ScheduledTaskPayload } from '../types';

function mapTask(row: Record<string, unknown>): ScheduledTask {
  const scheduleTimes = row.schedule_times as string[] | null | undefined;
  const scheduleAt = (row.schedule_at as string | null) ?? null;

  return {
    id: row.id as number,
    platform: row.platform as string,
    media_type: row.media_type as string,
    content_count: row.content_count as number,
    device_ids: (row.device_ids as Record<string, string>) ?? {},
    schedule_mode: row.schedule_mode as ScheduledTask['schedule_mode'],
    schedule_duration: (row.schedule_duration as ScheduleDuration) ?? 'day',
    schedule_times: scheduleTimes?.length ? scheduleTimes : scheduleAt ? [scheduleAt] : null,
    schedule_at: scheduleAt,
    posts_completed: (row.posts_completed as number) ?? 0,
    caption_enabled: (row.caption_enabled as boolean) ?? false,
    caption_prompt: (row.caption_prompt as string | null) ?? null,
    status: (row.status as ScheduledTask['status']) ?? 'pending',
    error: (row.error as string | null) ?? null,
    created_at: row.created_at as string,
  };
}

async function fetchPendingTasks(): Promise<ScheduledTask[]> {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from('scheduled_posts')
    .select('*')
    .eq('status', 'pending');

  if (error) throw error;
  return (data ?? []).map(mapTask);
}

export async function previewAutoScheduleTimes(
  contentCount: number,
  duration: ScheduleDuration = 'day',
): Promise<string[]> {
  const pendingTasks = await fetchPendingTasks();
  const baseTimes = generateAutoScheduleTimes(contentCount, pendingTasks);
  const expanded = expandTimesForDuration(baseTimes, duration);
  return resolveAllScheduleConflicts(expanded, pendingTasks);
}

export async function validateScheduleTimes(times: string[]): Promise<void> {
  const internalConflict = findInternalScheduleConflict(times);
  if (internalConflict !== null) {
    throw new ScheduleConflictError(
      `Post ${internalConflict} is too close to another post in this task. Keep at least ${MIN_TASK_GAP_MINUTES} minutes between each post.`,
    );
  }

  const pendingTasks = await fetchPendingTasks();
  const conflict = findPendingScheduleConflict(times, pendingTasks);

  if (conflict) {
    throw new ScheduleConflictError(
      `A pending task is already scheduled near ${formatScheduleTimeDisplay(conflict.time)}. Please change the time for post ${conflict.index} (at least ${MIN_TASK_GAP_MINUTES} minutes gap required).`,
    );
  }
}

export async function createScheduledTask(payload: ScheduledTaskPayload): Promise<ScheduledTask> {
  if (!supabase) {
    throw new Error('Supabase is not configured.');
  }

  const duration = payload.schedule_duration ?? 'day';
  const dayCount = getDurationDayCount(duration);
  const postsPerDay = payload.content_count;
  const pendingTasks = await fetchPendingTasks();

  let baseTimes: string[] | null = null;

  if (payload.schedule_mode === 'auto') {
    baseTimes = generateAutoScheduleTimes(postsPerDay, pendingTasks);
  } else if (payload.schedule_times?.length) {
    baseTimes = payload.schedule_times.map((t) => new Date(t).toISOString());
    await validateScheduleTimes(baseTimes);
  }

  let scheduleTimes: string[] | null = null;
  if (baseTimes) {
    const expanded = expandTimesForDuration(baseTimes, duration);
    scheduleTimes = resolveAllScheduleConflicts(expanded, pendingTasks);
  }

  const totalContentCount = postsPerDay * dayCount;

  const { data, error } = await supabase
    .from('scheduled_posts')
    .insert({
      platform: payload.platform,
      media_type: payload.media_type,
      content_count: totalContentCount,
      device_ids: payload.device_ids,
      schedule_mode: payload.schedule_mode,
      schedule_duration: duration,
      schedule_times: scheduleTimes,
      schedule_at: scheduleTimes?.[0] ?? null,
      caption_enabled: payload.caption_enabled,
      caption_prompt: payload.caption_prompt,
      status: 'pending',
    })
    .select()
    .single();

  if (error) throw error;
  return mapTask(data);
}

export async function fetchScheduledTasks(): Promise<ScheduledTask[]> {
  if (!supabase) {
    throw new Error('Supabase is not configured.');
  }

  const { data, error } = await supabase
    .from('scheduled_posts')
    .select('*')
    .order('created_at', { ascending: false });

  if (error) throw error;
  return (data ?? []).map(mapTask);
}

export async function deleteScheduledTask(id: number): Promise<void> {
  if (!supabase) {
    throw new Error('Supabase is not configured.');
  }

  const { error } = await supabase.from('scheduled_posts').delete().eq('id', id);
  if (error) throw error;
}

/** @deprecated Use createScheduledTask */
export const schedulePost = createScheduledTask;

export { getTaskScheduleTimes, formatScheduleTimeDisplay, normalizeScheduleMinute, generateAutoScheduleTimes };
