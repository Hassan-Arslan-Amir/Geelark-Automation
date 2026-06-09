import { useMemo, useState, useEffect } from 'react';
import { SearchBar } from './SearchBar';
import { Pagination } from './Pagination';
import { Select } from './Select';
import { Account } from '../types';
import { usePagination } from '../hooks/usePagination';
import { schedulePost } from '../hooks/useSchedulePost';
import {
  Platform,
  MediaType,
  PLATFORM_OPTIONS,
  getMediaTypesForPlatform,
} from '../constants/platforms';
import {
  CalendarClock,
  Check,
  Clock,
  Film,
  Hash,
  Image,
  Link2,
  Loader2,
  MessageSquare,
  Share2,
  Smartphone,
  User,
} from 'lucide-react';

interface SchedulePostScreenProps {
  accounts: Account[];
}

const inputClass =
  'w-full px-4 py-3 border border-surface-200 rounded-xl bg-surface-0 text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 transition-all text-sm';

const platformOptions = PLATFORM_OPTIONS.map(({ value, label }) => ({ value, label }));

function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatScheduleDisplay(value: string): string {
  if (!value) return 'Not set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Not set';
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

export function SchedulePostScreen({ accounts }: SchedulePostScreenProps) {
  const [platform, setPlatform] = useState<Platform>('instagram');
  const [mediaType, setMediaType] = useState<MediaType>('video');
  const [scheduleAt, setScheduleAt] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');
  const [caption, setCaption] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchCategory, setSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [searchQuery, setSearchQuery] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const supportedMediaTypes = getMediaTypesForPlatform(platform);
  const platformLabel = PLATFORM_OPTIONS.find((p) => p.value === platform)?.label ?? platform;

  const selectedAccounts = useMemo(
    () => accounts.filter((a) => selectedIds.has(a.profile_id)),
    [accounts, selectedIds],
  );

  useEffect(() => {
    if (!supportedMediaTypes.includes(mediaType)) {
      setMediaType(supportedMediaTypes[0]);
    }
  }, [platform, mediaType, supportedMediaTypes]);

  useEffect(() => {
    if (!scheduleAt) {
      const defaultTime = new Date(Date.now() + 60 * 60 * 1000);
      setScheduleAt(toDatetimeLocalValue(defaultTime));
    }
  }, [scheduleAt]);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    if (selectedIds.size === 0) {
      setFeedback({ type: 'error', message: 'Select at least one device.' });
      return;
    }

    if (!resourceUrl.trim()) {
      setFeedback({ type: 'error', message: 'Media URL is required.' });
      return;
    }

    const scheduledDate = new Date(scheduleAt);
    if (Number.isNaN(scheduledDate.getTime()) || scheduledDate.getTime() <= Date.now()) {
      setFeedback({ type: 'error', message: 'Schedule time must be in the future.' });
      return;
    }

    setSubmitting(true);
    try {
      await schedulePost({
        platform,
        media_type: mediaType,
        resource_url: resourceUrl.trim(),
        caption: caption.trim(),
        device_ids: buildDeviceIds(),
        schedule_at: scheduledDate.toISOString(),
      });

      setFeedback({
        type: 'success',
        message: `Scheduled for ${selectedIds.size} device${selectedIds.size !== 1 ? 's' : ''} on ${scheduledDate.toLocaleString()}.`,
      });
      setResourceUrl('');
      setCaption('');
      setSelectedIds(new Set());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to schedule post.';
      setFeedback({ type: 'error', message });
    } finally {
      setSubmitting(false);
    }
  };

  const checklist = [
    { label: 'Platform selected', done: !!platform },
    { label: 'Schedule time set', done: !!scheduleAt },
    { label: 'Media URL provided', done: !!resourceUrl.trim() },
    { label: 'At least one device', done: selectedIds.size > 0 },
  ];

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Schedule Post</h1>
          <p className="text-surface-500 mt-1 text-sm">
            Configure your post on the left, then pick devices on the right.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="flex flex-col xl:flex-row gap-6 lg:gap-8 items-start">
            {/* Left column — post details & summary */}
            <div className="w-full xl:w-[400px] xl:flex-shrink-0 xl:sticky xl:top-8 space-y-5">
              <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card space-y-5">
                <div className="flex items-center gap-2">
                  <CalendarClock size={18} className="text-brand-600" />
                  <h2 className="text-base font-bold text-surface-900">Post details</h2>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
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
                  </div>

                  <div>
                    <label htmlFor="scheduleAt" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                      Schedule time
                    </label>
                    <input
                      id="scheduleAt"
                      type="datetime-local"
                      value={scheduleAt}
                      onChange={(e) => setScheduleAt(e.target.value)}
                      className={inputClass}
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="resourceUrl" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                      Media URL
                    </label>
                    <input
                      id="resourceUrl"
                      type="url"
                      placeholder="https://cdn.example.com/video.mp4"
                      value={resourceUrl}
                      onChange={(e) => setResourceUrl(e.target.value)}
                      className={inputClass}
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="caption" className="block text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                      Caption
                    </label>
                    <textarea
                      id="caption"
                      rows={4}
                      placeholder="Write your post caption…"
                      value={caption}
                      onChange={(e) => setCaption(e.target.value)}
                      className={`${inputClass} resize-y min-h-[6rem]`}
                    />
                  </div>
                </div>
              </div>

              <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card space-y-4">
                <h2 className="text-base font-bold text-surface-900">Summary</h2>

                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-50 text-brand-700 text-xs font-semibold">
                    <Share2 size={12} />
                    {platformLabel}
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-100 text-surface-700 text-xs font-semibold">
                    {mediaType === 'video' ? <Film size={12} /> : <Image size={12} />}
                    {mediaType.charAt(0).toUpperCase() + mediaType.slice(1)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-100 text-surface-700 text-xs font-semibold">
                    <Smartphone size={12} />
                    {selectedIds.size} device{selectedIds.size !== 1 ? 's' : ''}
                  </span>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="flex items-start gap-2.5">
                    <Clock size={15} className="text-surface-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-[11px] font-semibold text-surface-400 uppercase tracking-wider">Scheduled for</p>
                      <p className="text-surface-800 font-medium">{formatScheduleDisplay(scheduleAt)}</p>
                    </div>
                  </div>

                  {resourceUrl.trim() && (
                    <div className="flex items-start gap-2.5">
                      <Link2 size={15} className="text-surface-400 mt-0.5 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold text-surface-400 uppercase tracking-wider">Media</p>
                        <p className="text-surface-600 font-mono text-xs truncate">{resourceUrl.trim()}</p>
                      </div>
                    </div>
                  )}

                  {caption.trim() && (
                    <div className="flex items-start gap-2.5">
                      <MessageSquare size={15} className="text-surface-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-[11px] font-semibold text-surface-400 uppercase tracking-wider">Caption</p>
                        <p className="text-surface-600 text-sm line-clamp-3">{caption.trim()}</p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-surface-100 space-y-2">
                  {checklist.map(({ label, done }) => (
                    <div key={label} className="flex items-center gap-2 text-sm">
                      <div
                        className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${
                          done ? 'bg-emerald-500' : 'bg-surface-200'
                        }`}
                      >
                        {done && <Check size={10} className="text-white" strokeWidth={3} />}
                      </div>
                      <span className={done ? 'text-surface-700 font-medium' : 'text-surface-400'}>{label}</span>
                    </div>
                  ))}
                </div>

                {feedback && (
                  <div
                    className={`rounded-xl px-4 py-3 text-sm font-medium ${
                      feedback.type === 'success'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-red-50 text-red-700 border border-red-200'
                    }`}
                  >
                    {feedback.message}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-brand-600/25 transition-colors"
                >
                  {submitting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Scheduling…
                    </>
                  ) : (
                    <>
                      <CalendarClock size={16} />
                      Schedule post
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Right column — device selection */}
            <div className="flex-1 min-w-0 w-full">
              <div className="bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card min-h-[32rem]">
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

                <div className="mb-5">
                  <SearchBar
                    category={searchCategory}
                    query={searchQuery}
                    onCategoryChange={setSearchCategory}
                    onQueryChange={setSearchQuery}
                  />
                </div>

                {selectedAccounts.length > 0 && (
                  <div className="mb-5 flex flex-wrap gap-2">
                    {selectedAccounts.slice(0, 8).map((account) => (
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
                    {selectedAccounts.length > 8 && (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-100 text-xs font-semibold text-surface-600">
                        +{selectedAccounts.length - 8} more
                      </span>
                    )}
                  </div>
                )}

                {filteredAccounts.length === 0 ? (
                  <div className="text-center py-16">
                    <Smartphone size={32} className="text-surface-300 mx-auto mb-3" />
                    <p className="text-surface-500 text-sm font-medium">No devices match your search.</p>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
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
          </div>
        </form>
      </div>
    </div>
  );
}
