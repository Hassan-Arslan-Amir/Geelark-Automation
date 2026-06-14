import { useMemo, useState } from 'react';
import { SearchBar } from './SearchBar';
import { Pagination } from './Pagination';
import { Account } from '../types';
import { usePagination } from '../hooks/usePagination';
import { syncDevicesFromGeelark } from '../hooks/useSyncDevices';
import { useAutoDismiss } from '../hooks/useAutoDismiss';
import { Eye, Heart, MessageCircle, ChevronRight, Smartphone, Hash, User, RefreshCw, Loader2 } from 'lucide-react';

interface DevicesScreenProps {
  accounts: Account[];
  searchCategory: 'username' | 'profile_id' | 'mobile';
  searchQuery: string;
  onSearchCategoryChange: (category: 'username' | 'profile_id' | 'mobile') => void;
  onSearchQueryChange: (query: string) => void;
  onDeviceClick: (account: Account) => void;
  onRefreshDevices: () => Promise<void>;
}

export function DevicesScreen({
  accounts,
  searchCategory,
  searchQuery,
  onSearchCategoryChange,
  onSearchQueryChange,
  onDeviceClick,
  onRefreshDevices,
}: DevicesScreenProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSyncDevices = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const result = await syncDevicesFromGeelark();
      await onRefreshDevices();
      setSyncMessage({
        type: 'success',
        text: result.message ?? `Synced ${result.total_in_json ?? 0} device(s) from GeeLark.`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to sync devices.';
      setSyncMessage({
        type: 'error',
        text: message.includes('fetch')
          ? `${message} Make sure the API server is running (python api_server.py).`
          : message,
      });
    } finally {
      setSyncing(false);
    }
  };

  useAutoDismiss(syncMessage, () => setSyncMessage(null));

  const getFieldValue = (account: Account, category: string): string => {
    if (category === 'username') return account.username;
    if (category === 'profile_id') return account.profile_id;
    if (category === 'mobile') return account.mobile;
    return '';
  };

  const totalViews = (account: Account): number => {
    return account.posts.reduce((sum, post) => sum + post.stats.views, 0);
  };

  const totalLikes = (account: Account): number => {
    return account.posts.reduce((sum, post) => sum + post.stats.likes, 0);
  };

  const totalComments = (account: Account): number => {
    return account.posts.reduce((sum, post) => sum + post.stats.comments, 0);
  };

  const filteredAccounts = useMemo(
    () =>
      accounts
        .filter((account) => {
          if (!searchQuery) return true;
          const fieldValue = getFieldValue(account, searchCategory).toLowerCase();
          return fieldValue.includes(searchQuery.toLowerCase());
        })
        .sort((a, b) => totalViews(b) - totalViews(a)),
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

  const totalFilteredViews    = filteredAccounts.reduce((sum, a) => sum + totalViews(a), 0);
  const totalFilteredLikes    = filteredAccounts.reduce((sum, a) => sum + totalLikes(a), 0);
  const totalFilteredComments = filteredAccounts.reduce((sum, a) => sum + totalComments(a), 0);

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 lg:mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Devices</h1>
            <p className="text-surface-500 mt-1 text-sm">
              {filteredAccounts.length} device{filteredAccounts.length !== 1 ? 's' : ''} found
            </p>
          </div>
          <button
            type="button"
            onClick={handleSyncDevices}
            disabled={syncing}
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-brand-600/25 transition-colors"
          >
            {syncing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Syncing from GeeLark…
              </>
            ) : (
              <>
                <RefreshCw size={16} />
                Sync devices
              </>
            )}
          </button>
        </div>

        {syncMessage && (
          <div
            className={`mb-6 rounded-xl px-4 py-3 text-sm font-medium border ${
              syncMessage.type === 'success'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-red-50 text-red-700 border-red-200'
            }`}
          >
            {syncMessage.text}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6 lg:mb-8 animate-fade-in">
          <div className="bg-surface-0 rounded-xl border border-surface-200/80 p-4 sm:p-5 shadow-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
                <Eye size={16} className="text-brand-600 sm:w-[18px] sm:h-[18px]" />
              </div>
              <div>
                <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider">Total Views</p>
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalFilteredViews.toLocaleString()}</p>
              </div>
            </div>
          </div>
          <div className="bg-surface-0 rounded-xl border border-surface-200/80 p-4 sm:p-5 shadow-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-rose-50 flex items-center justify-center flex-shrink-0">
                <Heart size={16} className="text-rose-500 sm:w-[18px] sm:h-[18px]" />
              </div>
              <div>
                <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider">Total Likes</p>
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalFilteredLikes.toLocaleString()}</p>
              </div>
            </div>
          </div>
          <div className="bg-surface-0 rounded-xl border border-surface-200/80 p-4 sm:p-5 shadow-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-teal-50 flex items-center justify-center flex-shrink-0">
                <MessageCircle size={16} className="text-teal-600 sm:w-[18px] sm:h-[18px]" />
              </div>
              <div>
                <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider">Total Comments</p>
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalFilteredComments.toLocaleString()}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-6 lg:mb-8 w-full sm:max-w-xl">
          <SearchBar
            category={searchCategory}
            query={searchQuery}
            onCategoryChange={onSearchCategoryChange}
            onQueryChange={onSearchQueryChange}
          />
        </div>

        {filteredAccounts.length === 0 ? (
          <div className="text-center py-16 sm:py-20 animate-fade-in">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-surface-100 flex items-center justify-center mx-auto mb-4">
              <Smartphone size={24} className="text-surface-300 sm:w-7 sm:h-7" />
            </div>
            <p className="text-surface-500 text-base font-medium">No devices found.</p>
            <p className="text-surface-400 text-sm mt-1">Try adjusting your search criteria.</p>
          </div>
        ) : (
          <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {paginatedAccounts.map((account, idx) => (
              <button
                key={account.profile_id}
                onClick={() => onDeviceClick(account)}
                className="group bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card hover:shadow-card-hover hover:border-brand-300 transition-all duration-300 text-left animate-slide-up"
                style={{ animationDelay: `${idx * 60}ms`, animationFillMode: 'both' }}
              >
                <div className="flex items-start justify-between mb-4 sm:mb-5">
                  <div className="flex items-center gap-3 sm:gap-3.5 min-w-0">
                    <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/30 transition-shadow flex-shrink-0">
                      <User size={18} className="text-white sm:w-5 sm:h-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm sm:text-base font-bold text-surface-900 truncate">
                        @{account.username}
                      </h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Hash size={11} className="text-surface-400 flex-shrink-0" />
                        <p className="text-[11px] sm:text-xs text-surface-400 font-mono truncate">
                          {account.profile_id}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-surface-50 group-hover:bg-brand-50 flex items-center justify-center transition-colors flex-shrink-0">
                    <ChevronRight size={14} className="text-surface-300 group-hover:text-brand-500 group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-4 sm:mb-5 pb-4 sm:pb-5 border-b border-surface-100">
                  <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-surface-50 flex items-center justify-center flex-shrink-0">
                    <Smartphone size={12} className="text-surface-500 sm:w-3.5 sm:h-3.5" />
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider">Mobile</p>
                    <p className="text-xs sm:text-sm text-surface-700 font-semibold">{account.mobile}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 sm:gap-4">
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Views</p>
                    <div className="flex items-center gap-1.5">
                      <Eye size={13} className="text-brand-500 sm:w-3.5 sm:h-3.5" />
                      <span className="text-sm sm:text-lg font-bold text-surface-900">{totalViews(account).toLocaleString()}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Likes</p>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm sm:text-lg font-bold text-surface-900">{totalLikes(account).toLocaleString()}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Comments</p>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm sm:text-lg font-bold text-surface-900">{totalComments(account).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </button>
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
