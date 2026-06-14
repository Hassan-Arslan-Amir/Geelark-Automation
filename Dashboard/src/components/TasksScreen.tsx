import { useMemo, useState, useCallback } from 'react';
import { Pagination } from './Pagination';
import { useScheduledTasks } from '../hooks/useScheduledTasks';
import { usePagination } from '../hooks/usePagination';
import { useAutoDismiss } from '../hooks/useAutoDismiss';
import { PLATFORM_OPTIONS } from '../constants/platforms';
import { ScheduledTask } from '../types';
import { getTaskScheduleTimes, SCHEDULE_DURATION_LABELS } from '../lib/scheduleTimes';
import {
  CalendarClock,
  Clock,
  Film,
  Image,
  Layers,
  ListTodo,
  Loader2,
  LucideIcon,
  Plus,
  Share2,
  Smartphone,
  Trash2,
  Zap,
} from 'lucide-react';

interface TasksScreenProps {
  onAddTask: () => void;
  highlightTaskId?: number | null;
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(iso));
}

function formatSchedule(task: ScheduledTask): string {
  if (task.schedule_mode === 'auto') {
    const times = getTaskScheduleTimes(task);
    if (times.length === 0) return 'Automatic';
    if (times.length === 1) return formatDate(times[0]);
    return `${times.length} scheduled times`;
  }
  const times = getTaskScheduleTimes(task);
  if (times.length === 0) return 'Manual — not set';
  if (times.length === 1) return formatDate(times[0]);
  return `${times.length} scheduled times`;
}

function platformLabel(platform: string): string {
  return PLATFORM_OPTIONS.find((p) => p.value === platform)?.label ?? platform;
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  running: 'bg-blue-50 text-blue-700 border-blue-200',
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  posted: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
};

function statusLabel(status: string): string {
  if (status === 'posted') return 'completed';
  return status;
}

/** Max post rows visible before the in-card list scrolls. */
const MAX_VISIBLE_POST_ROWS = 6;

export function TasksScreen({ onAddTask, highlightTaskId }: TasksScreenProps) {
  const { tasks, loading, refreshing, error, deletingId, refetch, deleteTask, clearError } = useScheduledTasks();
  const [actionError, setActionError] = useState<string | null>(null);

  const dismissErrors = useCallback(() => {
    setActionError(null);
    clearError();
  }, [clearError]);

  const displayError = actionError ?? error;
  useAutoDismiss(displayError, dismissErrors);

  const {
    paginatedItems: paginatedTasks,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    totalItems,
    rangeStart,
    rangeEnd,
  } = usePagination(tasks, []);

  const pendingCount = useMemo(
    () => tasks.filter((t) => t.status === 'pending' || t.status === 'running').length,
    [tasks],
  );

  const handleDelete = async (task: ScheduledTask) => {
    const confirmed = window.confirm(
      `Delete task #${task.id} (${platformLabel(task.platform)}, ${task.content_count} ${task.media_type}${task.content_count !== 1 ? 's' : ''})? This cannot be undone.`,
    );
    if (!confirmed) return;

    setActionError(null);
    try {
      await deleteTask(task.id);
    } catch {
      setActionError('Failed to delete task. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-surface-500 text-sm font-medium">Loading tasks…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 lg:mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Tasks</h1>
            <p className="text-surface-500 mt-1 text-sm flex items-center gap-2 flex-wrap">
              <span>
                {tasks.length} task{tasks.length !== 1 ? 's' : ''} total
                {pendingCount > 0 && ` · ${pendingCount} pending`}
              </span>
              {refreshing && (
                <span className="inline-flex items-center gap-1 text-surface-400">
                  <Loader2 size={12} className="animate-spin" />
                  Updating…
                </span>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onAddTask}
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 shadow-lg shadow-brand-600/25 transition-colors"
          >
            <Plus size={16} />
            Add new task
          </button>
        </div>

        {displayError && (
          <div className="mb-6 rounded-xl px-4 py-3 text-sm font-medium bg-red-50 text-red-700 border border-red-200 flex items-center justify-between gap-3">
            <span>{displayError}</span>
            <button type="button" onClick={() => refetch()} className="text-xs font-semibold underline hover:no-underline flex-shrink-0">
              Retry
            </button>
          </div>
        )}

        {tasks.length === 0 ? (
          <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-12 sm:p-16 shadow-card text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center mx-auto mb-4">
              <ListTodo size={28} className="text-surface-300" />
            </div>
            <p className="text-surface-700 text-base font-semibold mb-1">No tasks yet</p>
            <p className="text-surface-400 text-sm mb-6 max-w-sm mx-auto">
              Create your first posting task to schedule content across your devices.
            </p>
            <button
              type="button"
              onClick={onAddTask}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 shadow-lg shadow-brand-600/25 transition-colors"
            >
              <Plus size={16} />
              Add new task
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5 items-stretch">
              {paginatedTasks.map((task, idx) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  highlighted={task.id === highlightTaskId}
                  animationDelay={idx * 40}
                  deleting={deletingId === task.id}
                  onDelete={() => handleDelete(task)}
                />
              ))}
            </div>

            <Pagination
              page={page}
              totalPages={totalPages}
              totalItems={totalItems}
              rangeStart={rangeStart}
              rangeEnd={rangeEnd}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          </>
        )}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  highlighted,
  animationDelay,
  deleting,
  onDelete,
}: {
  task: ScheduledTask;
  highlighted: boolean;
  animationDelay: number;
  deleting: boolean;
  onDelete: () => void;
}) {
  const deviceCount = Object.keys(task.device_ids).length;
  const statusClass = STATUS_STYLES[task.status] ?? STATUS_STYLES.pending;
  const scheduleTimes = getTaskScheduleTimes(task);
  const postsDone = task.posts_completed ?? 0;
  const progressLabel =
    task.content_count > 1 ? `${postsDone}/${task.content_count} posted` : null;

  const hasScrollablePosts = scheduleTimes.length > MAX_VISIBLE_POST_ROWS;

  return (
    <div
      className={`bg-surface-0 rounded-2xl border p-5 sm:p-6 shadow-card animate-slide-up flex flex-col h-full min-h-[17.5rem] ${
        highlighted
          ? 'border-brand-400 ring-2 ring-brand-200 shadow-card-hover'
          : 'border-surface-200/80'
      } ${deleting ? 'opacity-60 pointer-events-none' : ''}`}
      style={{ animationDelay: `${animationDelay}ms`, animationFillMode: 'both' }}
    >
      <div className="flex items-start justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
            <Share2 size={16} className="text-brand-600" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-surface-900 truncate">{platformLabel(task.platform)}</p>
            <p className="text-[11px] text-surface-400 font-mono">#{task.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span
            className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider border ${statusClass} ${
              task.status === 'running' ? 'animate-pulse' : ''
            }`}
          >
            {statusLabel(task.status)}
          </span>
          <button
            type="button"
            onClick={onDelete}
            disabled={deleting}
            aria-label={`Delete task ${task.id}`}
            className="w-8 h-8 rounded-lg border border-surface-200 bg-surface-0 flex items-center justify-center text-surface-400 hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
          </button>
        </div>
      </div>

      <div className="space-y-2.5 mb-4 pb-4 border-b border-surface-100">
        <DetailRow
          icon={task.media_type === 'video' ? Film : Image}
          label="Media"
          value={task.media_type.charAt(0).toUpperCase() + task.media_type.slice(1)}
        />
        <DetailRow icon={Layers} label="Content" value={`${task.content_count} item${task.content_count !== 1 ? 's' : ''}`} />
        {progressLabel && (
          <DetailRow icon={ListTodo} label="Progress" value={progressLabel} />
        )}
        <DetailRow icon={Smartphone} label="Devices" value={`${deviceCount} selected`} />
        <DetailRow
          icon={task.schedule_mode === 'auto' ? Zap : Clock}
          label="Schedule"
          value={formatSchedule(task)}
        />
        {task.schedule_duration && task.schedule_duration !== 'day' && (
          <DetailRow
            icon={CalendarClock}
            label="Duration"
            value={SCHEDULE_DURATION_LABELS[task.schedule_duration]}
          />
        )}
      </div>

      {scheduleTimes.length > 1 && (
        <div className="mt-3 pt-3 border-t border-surface-100 flex flex-col min-h-0">
          <p className="text-[10px] font-semibold text-surface-400 uppercase tracking-wider mb-2">
            Post schedule · {scheduleTimes.length} total
          </p>
          <div
            className={`space-y-1.5 ${
              hasScrollablePosts
                ? 'max-h-[7.75rem] overflow-y-auto overscroll-contain pr-1 -mr-1'
                : ''
            }`}
          >
            {scheduleTimes.map((time, index) => (
              <div key={index} className="flex items-center justify-between gap-2 text-[11px]">
                <span className="text-surface-400 font-medium flex-shrink-0">Post {index + 1}</span>
                <span className="text-surface-600 font-semibold text-right truncate">{formatDate(time)}</span>
              </div>
            ))}
          </div>
          {hasScrollablePosts && (
            <p className="text-[10px] text-surface-400 mt-1.5">
              Showing {MAX_VISIBLE_POST_ROWS} at a time, scroll for more
            </p>
          )}
        </div>
      )}

      {task.error && (
        <p className="mt-3 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 line-clamp-2">
          {task.error}
        </p>
      )}

      <div className="flex items-center gap-1.5 text-[11px] text-surface-400 mt-auto pt-3">
        <CalendarClock size={12} />
        <span>Created {formatDate(task.created_at)}</span>
      </div>

      {highlighted && (
        <p className="mt-2 text-xs font-semibold text-brand-600">Just created</p>
      )}
    </div>
  );
}

function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <div className="flex items-center gap-1.5 text-surface-400">
        <Icon size={13} className="flex-shrink-0" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <span className="text-xs font-semibold text-surface-800 truncate">{value}</span>
    </div>
  );
}
