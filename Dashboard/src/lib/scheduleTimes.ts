import { ScheduleDuration, ScheduledTask } from '../types';

export const AUTO_FIRST_OFFSET_MINUTES = 10;
export const MIN_TASK_GAP_MINUTES = 20;
export const AUTO_INTRA_POST_GAP_MINUTES = 30;
/** When a slot conflicts with an existing task, shift ± this many minutes. */
export const CONFLICT_ADJUST_MINUTES = 30;

export const SCHEDULE_DURATION_DAYS: Record<ScheduleDuration, number> = {
  day: 1,
  week: 7,
  month: 30,
};

export const SCHEDULE_DURATION_LABELS: Record<ScheduleDuration, string> = {
  day: 'Single day',
  week: 'Week (7 days)',
  month: 'Month (30 days)',
};

const MINUTE_MS = 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

export function getDurationDayCount(duration: ScheduleDuration = 'day'): number {
  return SCHEDULE_DURATION_DAYS[duration] ?? 1;
}

/** Normalize to minute precision for conflict comparison. */
export function normalizeScheduleMinute(isoOrLocal: string | number): number {
  const d = new Date(isoOrLocal);
  d.setSeconds(0, 0);
  return d.getTime();
}

export function formatScheduleTimeDisplay(isoOrLocal: string): string {
  const date = new Date(isoOrLocal);
  if (Number.isNaN(date.getTime())) return 'Invalid time';
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

export function getTaskScheduleTimes(task: {
  schedule_times?: string[] | null;
  schedule_at?: string | null;
}): string[] {
  if (task.schedule_times?.length) return task.schedule_times;
  if (task.schedule_at) return [task.schedule_at];
  return [];
}

export function defaultScheduleTimes(count: number, startOffsetMs = 60 * 60 * 1000): string[] {
  const pad = (n: number) => String(n).padStart(2, '0');
  const toLocal = (date: Date) =>
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;

  const base = Date.now() + startOffsetMs;
  return Array.from({ length: count }, (_, i) =>
    toLocal(new Date(base + i * 60 * 60 * 1000)),
  );
}

export class ScheduleConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ScheduleConflictError';
  }
}

export function getPendingScheduleTimestampsMs(tasks: ScheduledTask[]): number[] {
  const timestamps: number[] = [];
  for (const task of tasks) {
    if (task.status !== 'pending') continue;
    for (const t of getTaskScheduleTimes(task)) {
      timestamps.push(normalizeScheduleMinute(t));
    }
  }
  return timestamps;
}

export function conflictsWithOccupied(
  candidateMs: number,
  occupiedMs: number[],
  minGapMinutes: number,
): boolean {
  const minGapMs = minGapMinutes * MINUTE_MS;
  return occupiedMs.some((t) => Math.abs(candidateMs - t) < minGapMs);
}

/**
 * Resolve a conflicting slot by trying ±minGapMinutes around occupied times,
 * then bumping forward until a free window is found.
 */
export function findNextAvailableSlot(
  startMs: number,
  occupiedMs: number[],
  minGapMinutes: number = CONFLICT_ADJUST_MINUTES,
): number {
  const candidate = normalizeScheduleMinute(startMs);
  const gapMs = minGapMinutes * MINUTE_MS;

  if (!conflictsWithOccupied(candidate, occupiedMs, minGapMinutes)) {
    return candidate;
  }

  const adjustments: number[] = [];
  for (const occupied of occupiedMs) {
    if (Math.abs(candidate - occupied) < gapMs) {
      adjustments.push(
        occupied - gapMs,
        occupied + gapMs,
        occupied - 2 * gapMs,
        occupied + 2 * gapMs,
      );
    }
  }

  adjustments.sort((a, b) => Math.abs(a - candidate) - Math.abs(b - candidate));

  for (const adj of adjustments) {
    const slot = normalizeScheduleMinute(adj);
    if (slot <= Date.now()) continue;
    if (!conflictsWithOccupied(slot, occupiedMs, minGapMinutes)) {
      return slot;
    }
  }

  let resolved = candidate;
  let adjusted = true;
  while (adjusted) {
    adjusted = false;
    for (const occupied of occupiedMs) {
      if (Math.abs(resolved - occupied) < gapMs) {
        resolved = normalizeScheduleMinute(occupied + gapMs);
        adjusted = true;
      }
    }
  }

  return resolved;
}

/** Repeat the same daily post times across multiple calendar days. */
export function expandTimesForDuration(
  baseTimes: string[],
  duration: ScheduleDuration = 'day',
): string[] {
  const days = getDurationDayCount(duration);
  if (days === 1) return baseTimes;

  const expanded: string[] = [];
  for (let day = 0; day < days; day++) {
    for (const time of baseTimes) {
      expanded.push(new Date(normalizeScheduleMinute(time) + day * DAY_MS).toISOString());
    }
  }
  return expanded;
}

/** Resolve conflicts for each time against pending tasks and earlier slots in the batch. */
export function resolveAllScheduleConflicts(
  times: string[],
  pendingTasks: ScheduledTask[],
  minGapMinutes: number = CONFLICT_ADJUST_MINUTES,
): string[] {
  const occupied = getPendingScheduleTimestampsMs(pendingTasks);
  const resolved: number[] = [];

  for (const time of times) {
    const slot = findNextAvailableSlot(
      normalizeScheduleMinute(time),
      [...occupied, ...resolved],
      minGapMinutes,
    );
    resolved.push(slot);
  }

  return resolved.map((t) => new Date(t).toISOString());
}

export function generateAutoScheduleTimes(
  contentCount: number,
  pendingTasks: ScheduledTask[],
  now = Date.now(),
): string[] {
  const occupied = getPendingScheduleTimestampsMs(pendingTasks);
  const times: number[] = [];

  const firstSlot = findNextAvailableSlot(
    now + AUTO_FIRST_OFFSET_MINUTES * MINUTE_MS,
    occupied,
    MIN_TASK_GAP_MINUTES,
  );
  times.push(firstSlot);

  for (let i = 1; i < contentCount; i++) {
    const targetStart = times[i - 1] + AUTO_INTRA_POST_GAP_MINUTES * MINUTE_MS;
    const slot = findNextAvailableSlot(targetStart, [...occupied, ...times], MIN_TASK_GAP_MINUTES);
    times.push(slot);
  }

  return times.map((t) => new Date(t).toISOString());
}

export function findInternalScheduleConflict(
  times: string[],
  minGapMinutes = MIN_TASK_GAP_MINUTES,
): number | null {
  const normalized = times.map((t) => normalizeScheduleMinute(t));

  for (let i = 0; i < normalized.length; i++) {
    for (let j = i + 1; j < normalized.length; j++) {
      if (Math.abs(normalized[i] - normalized[j]) < minGapMinutes * MINUTE_MS) {
        return j + 1;
      }
    }
  }
  return null;
}

export function findPendingScheduleConflict(
  newTimes: string[],
  pendingTasks: ScheduledTask[],
  minGapMinutes = MIN_TASK_GAP_MINUTES,
): { index: number; time: string } | null {
  const occupied = getPendingScheduleTimestampsMs(pendingTasks);

  for (let i = 0; i < newTimes.length; i++) {
    const candidate = normalizeScheduleMinute(newTimes[i]);
    const batchSoFar = newTimes.slice(0, i).map((t) => normalizeScheduleMinute(t));
    const allOccupied = [...occupied, ...batchSoFar];

    if (conflictsWithOccupied(candidate, allOccupied, minGapMinutes)) {
      return { index: i + 1, time: newTimes[i] };
    }
  }

  return null;
}

/** @deprecated Use findInternalScheduleConflict */
export function findInternalScheduleDuplicates(times: string[]): number | null {
  return findInternalScheduleConflict(times, 0);
}

/** @deprecated Use findPendingScheduleConflict */
export function findOccupiedSlot(
  newTimes: string[],
  occupiedMinutes: Set<number>,
): { index: number; time: string } | null {
  const occupied = [...occupiedMinutes];
  for (let i = 0; i < newTimes.length; i++) {
    const key = normalizeScheduleMinute(newTimes[i]);
    if (occupied.includes(key)) {
      return { index: i + 1, time: newTimes[i] };
    }
  }
  return null;
}

/** @deprecated Use getPendingScheduleTimestampsMs */
export function buildOccupiedMinutesFromTasks(tasks: ScheduledTask[]): Set<number> {
  return new Set(getPendingScheduleTimestampsMs(tasks));
}
