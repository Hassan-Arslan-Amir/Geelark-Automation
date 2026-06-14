import { useMemo, useState, useEffect } from 'react';
import { SearchBar } from './SearchBar';
import { Pagination } from './Pagination';
import { Select } from './Select';
import { Toggle } from './Toggle';
import { Account, ScheduleDuration, ScheduleMode } from '../types';
import { usePagination } from '../hooks/usePagination';
import { useBotSettings } from '../hooks/useBotSettings';
import { createScheduledTask, previewAutoScheduleTimes } from '../hooks/useSchedulePost';
import { useAutoDismiss } from '../hooks/useAutoDismiss';
import {
  AUTO_FIRST_OFFSET_MINUTES,
  AUTO_INTRA_POST_GAP_MINUTES,
  CONFLICT_ADJUST_MINUTES,
  defaultScheduleTimes,
  expandTimesForDuration,
  formatScheduleTimeDisplay,
  findInternalScheduleConflict,
  getDurationDayCount,
  MIN_TASK_GAP_MINUTES,
  SCHEDULE_DURATION_DAYS,
  SCHEDULE_DURATION_LABELS,
  ScheduleConflictError,
} from '../lib/scheduleTimes';
import {
  Platform,
  MediaType,
  PLATFORM_OPTIONS,
  getMediaTypesForPlatform,
} from '../constants/platforms';
import {
  Bot,
  Calendar,
  CalendarClock,
  CalendarRange,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Clock,
  Film,
  Hash,
  Image,
  Layers,
  Loader2,
  LucideIcon,
  PenLine,
  Share2,
  Smartphone,
  Sparkles,
  User,
  Zap,
} from 'lucide-react';

interface SchedulePostScreenProps {
  accounts: Account[];
  onTaskCreated: (taskId: number) => void;
}

type TabId = 'details' | 'schedule' | 'summary';

const TABS: { id: TabId; label: string; step: number }[] = [
  { id: 'details', label: 'Task details', step: 1 },
  { id: 'schedule', label: 'Schedule', step: 2 },
  { id: 'summary', label: 'Summary', step: 3 },
];

const inputClass =
  'w-full px-4 py-3 border border-surface-200 rounded-xl bg-surface-0 text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 transition-all text-sm';

const platformOptions = PLATFORM_OPTIONS.map(({ value, label }) => ({ value, label }));

const DURATION_OPTIONS: {
  value: ScheduleDuration;
  label: string;
  description: string;
  icon: LucideIcon;
}[] = [
  {
    value: 'day',
    label: SCHEDULE_DURATION_LABELS.day,
    description: 'Post once on the selected day — same as today.',
    icon: Calendar,
  },
  {
    value: 'week',
    label: SCHEDULE_DURATION_LABELS.week,
    description: 'Repeat the same daily schedule for the next 7 days.',
    icon: CalendarClock,
  },
  {
    value: 'month',
    label: SCHEDULE_DURATION_LABELS.month,
    description: 'Repeat the same daily schedule for the next 30 days.',
    icon: CalendarRange,
  },
];

const DEFAULT_CAPTION_PROMPT =
  'Write an engaging social media caption for this content. Keep it concise, include relevant hashtags, and match a friendly tone.';

function formatScheduleSummary(
  mode: ScheduleMode,
  duration: ScheduleDuration,
  postsPerDay: number,
  times: string[],
): string {
  const dayCount = getDurationDayCount(duration);
  const durationLabel = dayCount === 1 ? '1 day' : `${dayCount} days`;

  if (mode === 'auto') {
    if (times.length === 0) return 'Calculating…';
    if (dayCount === 1 && times.length === 1) return formatScheduleTimeDisplay(times[0]);
    return `${postsPerDay}/day × ${durationLabel} · ${times.length} total posts`;
  }
  if (times.length === 0) return 'Not set';
  if (dayCount === 1 && times.length === 1) return formatScheduleTimeDisplay(times[0]);
  return `${postsPerDay}/day × ${durationLabel} · ${times.length} total posts`;
}

export function SchedulePostScreen({ accounts, onTaskCreated }: SchedulePostScreenProps) {
  const { settings: botSettings } = useBotSettings();
  const [activeTab, setActiveTab] = useState<TabId>('details');
  const [platform, setPlatform] = useState<Platform>('instagram');
  const [mediaType, setMediaType] = useState<MediaType>('video');
  const [contentCount, setContentCount] = useState(1);
  const [captionEnabled, setCaptionEnabled] = useState(false);
  const [captionPrompt, setCaptionPrompt] = useState(DEFAULT_CAPTION_PROMPT);
  const [scheduleMode, setScheduleMode] = useState<ScheduleMode>('auto');
  const [scheduleDuration, setScheduleDuration] = useState<ScheduleDuration>('day');
  const [scheduleTimes, setScheduleTimes] = useState<string[]>(() => defaultScheduleTimes(1));
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchCategory, setSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [searchQuery, setSearchQuery] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [autoPreviewTimes, setAutoPreviewTimes] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ type: 'error'; message: string } | null>(null);

  useAutoDismiss(feedback, () => setFeedback(null));

  const supportedMediaTypes = getMediaTypesForPlatform(platform);
  const platformLabel = PLATFORM_OPTIONS.find((p) => p.value === platform)?.label ?? platform;
  const activeTabIndex = TABS.findIndex((t) => t.id === activeTab);

  const selectedAccounts = useMemo(
    () => accounts.filter((a) => selectedIds.has(a.profile_id)),
    [accounts, selectedIds],
  );

  const manualPreviewTimes = useMemo(() => {
    if (scheduleMode !== 'manual' || scheduleTimes.length === 0) return [];
    const base = scheduleTimes.map((t) => new Date(t).toISOString());
    return expandTimesForDuration(base, scheduleDuration);
  }, [scheduleMode, scheduleDuration, scheduleTimes]);

  const displayPreviewTimes =
    scheduleMode === 'manual' ? manualPreviewTimes : autoPreviewTimes;

  useEffect(() => {
    if (!supportedMediaTypes.includes(mediaType)) {
      setMediaType(supportedMediaTypes[0]);
    }
  }, [platform, mediaType, supportedMediaTypes]);

  useEffect(() => {
    setScheduleTimes((prev) => {
      const defaults = defaultScheduleTimes(contentCount);
      return defaults.map((d, i) => prev[i] || d);
    });
  }, [contentCount]);

  useEffect(() => {
    if (scheduleMode !== 'auto' || activeTab !== 'summary') return;

    let cancelled = false;
    previewAutoScheduleTimes(contentCount, scheduleDuration)
      .then((times) => {
        if (!cancelled) setAutoPreviewTimes(times);
      })
      .catch(() => {
        if (!cancelled) setAutoPreviewTimes([]);
      });

    return () => {
      cancelled = true;
    };
  }, [scheduleMode, scheduleDuration, activeTab, contentCount]);

  const getFieldValue = (account: Account, category: string): string => {
    if (category === 'username') return account.username;
    if (category === 'profile_id') return account.profile_id;
    if (category === 'mobile') return account.mobile;
    return '';
  };

  const filteredAccounts = useMemo(
    () =>
      accounts.filter((account) => {
        if (!searchQuery) return true;
        const fieldValue = getFieldValue(account, searchCategory).toLowerCase();
        return fieldValue.includes(searchQuery.toLowerCase());
      }),
    [accounts, searchQuery, searchCategory],
  );

  const {
    paginatedItems: paginatedAccounts,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    totalItems,
    rangeStart,
    rangeEnd,
  } = usePagination(filteredAccounts, [searchQuery, searchCategory]);

  const toggleDevice = (profileId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(profileId)) next.delete(profileId);
      else next.add(profileId);
      return next;
    });
  };

  const selectAllFiltered = () => {
    setSelectedIds(new Set(filteredAccounts.map((a) => a.profile_id)));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const buildDeviceIds = (): Record<string, string> => {
    const map: Record<string, string> = {};
    for (const account of accounts) {
      if (selectedIds.has(account.profile_id)) {
        map[account.mobile] = account.profile_id;
      }
    }
    return map;
  };

  const validateDetailsTab = (): string | null => {
    if (contentCount < 1) return 'Content count must be at least 1.';
    if (selectedIds.size === 0) return 'Select at least one device.';
    if (captionEnabled && !captionPrompt.trim()) {
      return 'Caption prompt is required when caption generation is enabled.';
    }
    if (captionEnabled && !botSettings.openai_api_key.trim()) {
      return 'Add your OpenAI API key in Settings before enabling captions.';
    }
    return null;
  };

  const updateScheduleTime = (index: number, value: string) => {
    setScheduleTimes((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const validateScheduleTab = (): string | null => {
    if (scheduleMode !== 'manual') return null;

    if (scheduleTimes.length !== contentCount) {
      return 'Set a schedule time for each post.';
    }

    for (let i = 0; i < scheduleTimes.length; i++) {
      const scheduledDate = new Date(scheduleTimes[i]);
      if (Number.isNaN(scheduledDate.getTime())) {
        return `Enter a valid schedule time for post ${i + 1}.`;
      }
      if (scheduledDate.getTime() <= Date.now()) {
        return `Post ${i + 1} must be scheduled in the future.`;
      }
    }

    const isoTimes = scheduleTimes.map((t) => new Date(t).toISOString());
    const conflictIndex = findInternalScheduleConflict(isoTimes);
    if (conflictIndex !== null) {
      return `Post ${conflictIndex} is too close to another post. Keep at least ${MIN_TASK_GAP_MINUTES} minutes between each post.`;
    }

    return null;
  };

  const goNext = () => {
    setFeedback(null);
    if (activeTab === 'details') {
      const err = validateDetailsTab();
      if (err) { setFeedback({ type: 'error', message: err }); return; }
      setActiveTab('schedule');
    } else if (activeTab === 'schedule') {
      const err = validateScheduleTab();
      if (err) { setFeedback({ type: 'error', message: err }); return; }
      setActiveTab('summary');
    }
  };

  const goBack = () => {
    setFeedback(null);
    if (activeTab === 'schedule') setActiveTab('details');
    else if (activeTab === 'summary') setActiveTab('schedule');
  };

  const resetForm = () => {
    setPlatform('instagram');
    setMediaType('video');
    setContentCount(1);
    setCaptionEnabled(false);
    setCaptionPrompt(DEFAULT_CAPTION_PROMPT);
    setScheduleMode('auto');
    setScheduleDuration('day');
    setScheduleTimes(defaultScheduleTimes(1));
    setSelectedIds(new Set());
    setSearchQuery('');
    setActiveTab('details');
  };

  const handleCreateTask = async () => {
    setFeedback(null);

    const detailsErr = validateDetailsTab();
    if (detailsErr) { setFeedback({ type: 'error', message: detailsErr }); setActiveTab('details'); return; }

    const scheduleErr = validateScheduleTab();
    if (scheduleErr) { setFeedback({ type: 'error', message: scheduleErr }); setActiveTab('schedule'); return; }

    setSubmitting(true);
    try {
      const isoTimes =
        scheduleMode === 'manual'
          ? scheduleTimes.map((t) => new Date(t).toISOString())
          : null;

      const task = await createScheduledTask({
        platform,
        media_type: mediaType,
        content_count: contentCount,
        device_ids: buildDeviceIds(),
        schedule_mode: scheduleMode,
        schedule_duration: scheduleDuration,
        schedule_times: isoTimes,
        caption_enabled: captionEnabled,
        caption_prompt: captionEnabled ? captionPrompt.trim() : null,
      });

      resetForm();
      onTaskCreated(task.id);
    } catch (err) {
      if (err instanceof ScheduleConflictError) {
        setFeedback({ type: 'error', message: err.message });
        setActiveTab('schedule');
        return;
      }
      const message = err instanceof Error ? err.message : 'Failed to create task.';
      setFeedback({ type: 'error', message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Schedule Post</h1>
          <p className="text-surface-500 mt-1 text-sm">
            Create a posting task in three steps — details, schedule, then review.
          </p>
        </div>

        {/* Tab stepper */}
        <div className="mb-6 lg:mb-8">
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-0">
            {TABS.map((tab, idx) => {
              const isActive = activeTab === tab.id;
              const isComplete = idx < activeTabIndex;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    if (idx <= activeTabIndex) {
                      setFeedback(null);
                      setActiveTab(tab.id);
                    }
                  }}
                  disabled={idx > activeTabIndex}
                  className={`flex-1 flex items-center gap-3 px-4 py-3 sm:py-4 rounded-xl sm:rounded-none sm:first:rounded-l-xl sm:last:rounded-r-xl border transition-all duration-200 ${
                    isActive
                      ? 'bg-brand-600 border-brand-600 text-white shadow-lg shadow-brand-600/20 z-10'
                      : isComplete
                        ? 'bg-brand-50 border-brand-200 text-brand-700 hover:bg-brand-100 cursor-pointer'
                        : 'bg-surface-0 border-surface-200 text-surface-400 cursor-not-allowed'
                  } ${idx > 0 ? 'sm:-ml-px' : ''}`}
                >
                  <span
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : isComplete
                          ? 'bg-brand-600 text-white'
                          : 'bg-surface-100 text-surface-400'
                    }`}
                  >
                    {isComplete ? <Check size={14} strokeWidth={3} /> : tab.step}
                  </span>
                  <span className="text-sm font-semibold truncate">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {feedback?.type === 'error' && (
          <div className="mb-6 rounded-xl px-4 py-3 text-sm font-medium bg-red-50 text-red-700 border border-red-200">
            {feedback.message}
          </div>
        )}

        {/* Tab 1 — Task details */}
        {activeTab === 'details' && (
          <div className="space-y-6 animate-fade-in">
            <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
              <div className="flex items-center gap-2 mb-5">
                <ClipboardList size={18} className="text-brand-600" />
                <h2 className="text-base font-bold text-surface-900">Task configuration</h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="platform" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                    Platform
                  </label>
                  <Select
                    id="platform"
                    value={platform}
                    options={platformOptions}
                    onChange={setPlatform}
                    aria-label="Platform"
                  />
                </div>
                <div>
                  <label htmlFor="mediaType" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                    Media type
                  </label>
                  <Select
                    id="mediaType"
                    value={mediaType}
                    options={supportedMediaTypes.map((type) => ({
                      value: type,
                      label: type.charAt(0).toUpperCase() + type.slice(1),
                    }))}
                    onChange={setMediaType}
                    aria-label="Media type"
                  />
                </div>
                <div>
                  <label htmlFor="contentCount" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                    Content count
                  </label>
                  <input
                    id="contentCount"
                    type="number"
                    min={1}
                    max={100}
                    value={contentCount}
                    onChange={(e) => setContentCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
                    className={inputClass}
                  />
                  <p className="text-xs text-surface-400 mt-1.5">
                    Number of {mediaType === 'video' ? 'videos' : 'images'} to post from Google Drive.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
              <div className="flex items-start justify-between gap-4 mb-5">
                <div className="flex items-start gap-2">
                  <Sparkles size={18} className="text-brand-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h2 className="text-base font-bold text-surface-900">AI caption generation</h2>
                    <p className="text-sm text-surface-500 mt-0.5">
                      Generate a caption for this task using OpenAI and your API key from Settings.
                    </p>
                  </div>
                </div>
                <Toggle
                  id="captionEnabled"
                  checked={captionEnabled}
                  onChange={setCaptionEnabled}
                  aria-label="Enable AI caption generation for this task"
                />
              </div>

              <div
                className={`grid transition-all duration-300 ease-in-out ${
                  captionEnabled ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                }`}
              >
                <div className="overflow-hidden">
                  <div className={`pt-4 border-t border-surface-100 ${captionEnabled ? '' : 'pointer-events-none'}`}>
                    <label htmlFor="captionPrompt" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                      Caption prompt
                    </label>
                    <textarea
                      id="captionPrompt"
                      rows={5}
                      placeholder="Describe how the AI should write captions for this task…"
                      value={captionPrompt}
                      onChange={(e) => setCaptionPrompt(e.target.value)}
                      className={`${inputClass} resize-y min-h-[8rem]`}
                    />
                    <p className="text-xs text-surface-400 mt-2">
                      This prompt is sent to OpenAI along with your content when the task runs.
                    </p>
                  </div>
                </div>
              </div>

              {!captionEnabled && (
                <div className="flex items-center gap-2 mt-2 px-3 py-2.5 rounded-xl bg-surface-50 border border-surface-100">
                  <Bot size={15} className="text-surface-400 flex-shrink-0" />
                  <p className="text-xs text-surface-500">
                    Captions are off for this task. Posts will go out without AI-generated text.
                  </p>
                </div>
              )}
            </div>

            <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
                <div>
                  <h2 className="text-base font-bold text-surface-900">Select devices</h2>
                  <p className="text-sm text-surface-500 mt-0.5">
                    {selectedIds.size} of {accounts.length} selected
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={selectAllFiltered}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-surface-200 text-surface-600 hover:bg-surface-50 transition-colors"
                  >
                    Select all{searchQuery ? ' filtered' : ''}
                  </button>
                  <button
                    type="button"
                    onClick={clearSelection}
                    disabled={selectedIds.size === 0}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-surface-200 text-surface-600 hover:bg-surface-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="mb-5 max-w-xl">
                <SearchBar
                  category={searchCategory}
                  query={searchQuery}
                  onCategoryChange={setSearchCategory}
                  onQueryChange={setSearchQuery}
                />
              </div>

              {selectedAccounts.length > 0 && (
                <div className="mb-5 flex flex-wrap gap-2">
                  {selectedAccounts.slice(0, 10).map((account) => (
                    <span
                      key={account.profile_id}
                      className="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-full bg-brand-50 border border-brand-200 text-xs font-semibold text-brand-700"
                    >
                      @{account.username}
                      <button
                        type="button"
                        onClick={() => toggleDevice(account.profile_id)}
                        className="w-4 h-4 rounded-full hover:bg-brand-200 flex items-center justify-center text-brand-600 transition-colors"
                        aria-label={`Remove ${account.username}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  {selectedAccounts.length > 10 && (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-100 text-xs font-semibold text-surface-600">
                      +{selectedAccounts.length - 10} more
                    </span>
                  )}
                </div>
              )}

              {filteredAccounts.length === 0 ? (
                <div className="text-center py-12">
                  <Smartphone size={32} className="text-surface-300 mx-auto mb-3" />
                  <p className="text-surface-500 text-sm font-medium">No devices match your search.</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {paginatedAccounts.map((account) => {
                      const selected = selectedIds.has(account.profile_id);
                      return (
                        <button
                          key={account.profile_id}
                          type="button"
                          onClick={() => toggleDevice(account.profile_id)}
                          className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-all duration-200 ${
                            selected
                              ? 'border-brand-400 bg-brand-50/50 shadow-sm ring-1 ring-brand-200'
                              : 'border-surface-200 bg-surface-0 hover:border-brand-200 hover:bg-surface-50'
                          }`}
                        >
                          <div
                            className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                              selected ? 'bg-brand-600 border-brand-600' : 'border-surface-300 bg-surface-0'
                            }`}
                          >
                            {selected && <Check size={12} className="text-white" strokeWidth={3} />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <User size={14} className="text-brand-500 flex-shrink-0" />
                              <p className="text-sm font-bold text-surface-900 truncate">@{account.username}</p>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                              <Hash size={11} className="text-surface-400 flex-shrink-0" />
                              <p className="text-xs text-surface-400 font-mono truncate">{account.profile_id}</p>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                              <Smartphone size={11} className="text-surface-400 flex-shrink-0" />
                              <p className="text-xs text-surface-500">{account.mobile}</p>
                            </div>
                          </div>
                        </button>
                      );
                    })}
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
        )}

        {/* Tab 2 — Schedule */}
        {activeTab === 'schedule' && (
          <div className="animate-fade-in max-w-5xl mx-auto w-full">
            <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 lg:p-8 shadow-card">
              <div className="flex items-center gap-2 mb-6">
                <Clock size={18} className="text-brand-600" />
                <h2 className="text-base font-bold text-surface-900">When should posting start?</h2>
              </div>

              <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-3">
                How long should this run?
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
                {DURATION_OPTIONS.map(({ value, label, description, icon: Icon }) => {
                  const selected = scheduleDuration === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setScheduleDuration(value)}
                      className={`p-4 rounded-xl border-2 text-left transition-all duration-200 ${
                        selected
                          ? 'border-brand-500 bg-brand-50/60 shadow-sm ring-1 ring-brand-200'
                          : 'border-surface-200 bg-surface-0 hover:border-brand-200 hover:bg-surface-50'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 mb-2">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                          selected ? 'bg-brand-600 text-white' : 'bg-surface-100 text-surface-500'
                        }`}>
                          <Icon size={16} />
                        </div>
                        <p className="text-sm font-bold text-surface-900">{label}</p>
                        {selected && (
                          <Check size={16} className="text-brand-600 ml-auto flex-shrink-0" strokeWidth={2.5} />
                        )}
                      </div>
                      <p className="text-xs text-surface-600 leading-relaxed">{description}</p>
                    </button>
                  );
                })}
              </div>

              <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-3">
                Scheduling mode
              </p>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 mb-6">
                <button
                  type="button"
                  onClick={() => setScheduleMode('auto')}
                  className={`p-5 rounded-xl border-2 text-left transition-all duration-200 ${
                    scheduleMode === 'auto'
                      ? 'border-brand-500 bg-brand-50/60 shadow-sm ring-1 ring-brand-200'
                      : 'border-surface-200 bg-surface-0 hover:border-brand-200 hover:bg-surface-50'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      scheduleMode === 'auto' ? 'bg-brand-600 text-white' : 'bg-surface-100 text-surface-500'
                    }`}>
                      <Zap size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-surface-900">Auto</p>
                      <p className="text-xs text-surface-500">Recommended</p>
                    </div>
                    {scheduleMode === 'auto' && (
                      <Check size={18} className="text-brand-600 ml-auto flex-shrink-0" strokeWidth={2.5} />
                    )}
                  </div>
                  <p className="text-sm text-surface-600 leading-relaxed">
                    First post schedules {AUTO_FIRST_OFFSET_MINUTES} minutes from now. Each post in this task is spaced {AUTO_INTRA_POST_GAP_MINUTES} minutes apart.
                    {scheduleDuration !== 'day' && (
                      <> The same daily pattern repeats for {SCHEDULE_DURATION_DAYS[scheduleDuration]} days.</>
                    )}
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setScheduleMode('manual')}
                  className={`p-5 rounded-xl border-2 text-left transition-all duration-200 ${
                    scheduleMode === 'manual'
                      ? 'border-brand-500 bg-brand-50/60 shadow-sm ring-1 ring-brand-200'
                      : 'border-surface-200 bg-surface-0 hover:border-brand-200 hover:bg-surface-50'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      scheduleMode === 'manual' ? 'bg-brand-600 text-white' : 'bg-surface-100 text-surface-500'
                    }`}>
                      <PenLine size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-surface-900">Manual</p>
                      <p className="text-xs text-surface-500">Custom time</p>
                    </div>
                    {scheduleMode === 'manual' && (
                      <Check size={18} className="text-brand-600 ml-auto flex-shrink-0" strokeWidth={2.5} />
                    )}
                  </div>
                  <p className="text-sm text-surface-600 leading-relaxed">
                    You choose the exact date and time for each post on day one.
                    {scheduleDuration !== 'day' && (
                      <> The same times repeat on the following {SCHEDULE_DURATION_DAYS[scheduleDuration] - 1} day(s).</>
                    )}
                  </p>
                </button>
              </div>

              {scheduleMode === 'manual' && (
                <div className="pt-6 border-t border-surface-100 animate-fade-in">
                  <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-4">
                    Day-one schedule for each {mediaType}
                    {scheduleDuration !== 'day' && (
                      <span className="normal-case font-normal text-surface-400">
                        {' '}· repeated for {SCHEDULE_DURATION_DAYS[scheduleDuration]} days
                      </span>
                    )}
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {scheduleTimes.map((time, index) => (
                      <div key={index}>
                        <label
                          htmlFor={`scheduleAt-${index}`}
                          className="block text-xs font-semibold text-surface-600 mb-2"
                        >
                          Post {index + 1} of {contentCount}
                        </label>
                        <input
                          id={`scheduleAt-${index}`}
                          type="datetime-local"
                          value={time}
                          onChange={(e) => updateScheduleTime(index, e.target.value)}
                          className={inputClass}
                          required
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {scheduleMode === 'auto' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
                  <div className="flex items-start gap-3 px-4 py-3.5 rounded-xl bg-surface-50 border border-surface-100">
                    <Bot size={16} className="text-brand-500 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-surface-600 leading-relaxed">
                      Times are assigned automatically. If a slot is taken, the bot shifts it ±{CONFLICT_ADJUST_MINUTES} minutes or finds the next free window.
                    </p>
                  </div>
                  <div className="flex items-start gap-3 px-4 py-3.5 rounded-xl bg-brand-50/50 border border-brand-100">
                    <Zap size={16} className="text-brand-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-surface-600 leading-relaxed space-y-1">
                      <p>
                        <span className="font-semibold text-surface-800">First post:</span>{' '}
                        {AUTO_FIRST_OFFSET_MINUTES} minutes from task creation
                      </p>
                      <p>
                        <span className="font-semibold text-surface-800">Between posts:</span>{' '}
                        {AUTO_INTRA_POST_GAP_MINUTES} minutes in this task
                      </p>
                      <p>
                        <span className="font-semibold text-surface-800">Across tasks:</span>{' '}
                        {MIN_TASK_GAP_MINUTES} minute minimum gap
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3 — Summary */}
        {activeTab === 'summary' && (
          <div className="animate-fade-in max-w-5xl mx-auto w-full grid grid-cols-1 xl:grid-cols-5 gap-6">
            <div className="xl:col-span-3 bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 lg:p-8 shadow-card space-y-6">
              <div className="flex items-center gap-2">
                <CalendarClock size={18} className="text-brand-600" />
                <h2 className="text-base font-bold text-surface-900">Task summary</h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <SummaryRow icon={Share2} label="Platform" value={platformLabel} />
                <SummaryRow
                  icon={mediaType === 'video' ? Film : Image}
                  label="Media type"
                  value={mediaType.charAt(0).toUpperCase() + mediaType.slice(1)}
                />
                <SummaryRow icon={Layers} label="Content count" value={`${contentCount} ${mediaType}${contentCount !== 1 ? 's' : ''}`} />
                <SummaryRow icon={Smartphone} label="Devices" value={`${selectedIds.size} selected`} />
                <SummaryRow
                  icon={Sparkles}
                  label="AI caption"
                  value={captionEnabled ? 'Enabled' : 'Disabled'}
                />
                <SummaryRow
                  icon={scheduleMode === 'auto' ? Zap : Clock}
                  label="Schedule mode"
                  value={scheduleMode === 'auto' ? 'Automatic' : 'Manual'}
                />
                <SummaryRow
                  icon={CalendarRange}
                  label="Duration"
                  value={SCHEDULE_DURATION_LABELS[scheduleDuration]}
                />
                <SummaryRow
                  icon={Clock}
                  label="Schedule"
                  value={formatScheduleSummary(
                    scheduleMode,
                    scheduleDuration,
                    contentCount,
                    displayPreviewTimes.length > 0
                      ? displayPreviewTimes
                      : scheduleMode === 'manual'
                        ? scheduleTimes.map((t) => new Date(t).toISOString())
                        : autoPreviewTimes,
                  )}
                />
              </div>

              {displayPreviewTimes.length > 0 && (
                <div className="pt-4 border-t border-surface-100">
                  <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-3">
                    {scheduleMode === 'auto' ? 'Estimated post schedule' : 'Post schedule'}
                    {scheduleDuration !== 'day' && (
                      <span className="normal-case font-normal text-surface-400">
                        {' '}· {contentCount} post{contentCount !== 1 ? 's' : ''} per day
                      </span>
                    )}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                    {displayPreviewTimes.map((time, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-surface-50 border border-surface-100 text-sm"
                      >
                        <span className="text-xs font-semibold text-surface-500">Post {index + 1}</span>
                        <span className="text-xs font-semibold text-surface-800">
                          {formatScheduleTimeDisplay(time)}
                        </span>
                      </div>
                    ))}
                  </div>
                  {scheduleDuration !== 'day' && (
                    <p className="text-xs text-surface-400 mt-2">
                      Showing all {displayPreviewTimes.length} scheduled slots across{' '}
                      {getDurationDayCount(scheduleDuration)} days
                      {scheduleMode === 'auto' ? ' (conflicts adjusted at save time)' : ''}.
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="xl:col-span-2 space-y-6">
              {selectedAccounts.length > 0 && (
                <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
                  <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-3">
                    Selected devices ({selectedAccounts.length})
                  </p>
                  <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                    {selectedAccounts.map((account) => (
                      <span
                        key={account.profile_id}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-100 text-xs font-semibold text-surface-700"
                      >
                        <Smartphone size={11} className="text-brand-500" />
                        {account.mobile}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card">
                <p className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-4">Readiness</p>
                <div className="space-y-3">
                  {[
                    { label: 'Platform & media configured', done: true },
                    { label: 'Content count set', done: contentCount >= 1 },
                    { label: 'Devices selected', done: selectedIds.size > 0 },
                    {
                      label: captionEnabled ? 'Caption prompt set' : 'Caption generation off',
                      done: !captionEnabled || (captionPrompt.trim().length > 0 && botSettings.openai_api_key.trim().length > 0),
                    },
                    { label: 'Schedule configured', done: scheduleMode === 'auto' || validateScheduleTab() === null },
                  ].map(({ label, done }) => (
                    <div key={label} className="flex items-center gap-2.5 text-sm">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${done ? 'bg-emerald-500' : 'bg-surface-200'}`}>
                        {done && <Check size={11} className="text-white" strokeWidth={3} />}
                      </div>
                      <span className={done ? 'text-surface-700 font-medium' : 'text-surface-400'}>{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation footer */}
        <div className="mt-8 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <button
            type="button"
            onClick={goBack}
            disabled={activeTab === 'details'}
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl border border-surface-200 bg-surface-0 text-surface-700 font-semibold text-sm hover:bg-surface-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={16} />
            Back
          </button>

          {activeTab !== 'summary' ? (
            <button
              type="button"
              onClick={goNext}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 shadow-lg shadow-brand-600/25 transition-colors"
            >
              Continue
              <ChevronRight size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCreateTask}
              disabled={submitting}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-brand-600/25 transition-colors"
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Creating task…
                </>
              ) : (
                <>
                  <CalendarClock size={16} />
                  Create task
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-surface-50 border border-surface-100">
      <div className="w-9 h-9 rounded-lg bg-surface-0 border border-surface-200 flex items-center justify-center flex-shrink-0">
        <Icon size={16} className="text-brand-600" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-surface-400 uppercase tracking-wider">{label}</p>
        <p className="text-sm font-semibold text-surface-900 mt-0.5">{value}</p>
      </div>
    </div>
  );
}
