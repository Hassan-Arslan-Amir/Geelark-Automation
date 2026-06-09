import { ChevronLeft, ChevronRight } from 'lucide-react';
import { PAGE_SIZE_OPTIONS, PageSize } from '../hooks/usePagination';
import { Select } from './Select';

interface PaginationProps {
  page: number;
  totalPages: number;
  totalItems: number;
  rangeStart: number;
  rangeEnd: number;
  pageSize: PageSize;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: PageSize) => void;
}

export function Pagination({
  page,
  totalPages,
  totalItems,
  rangeStart,
  rangeEnd,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  if (totalItems === 0) return null;

  return (
    <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
      <p className="text-sm text-surface-500 order-2 sm:order-1">
        Showing <span className="font-semibold text-surface-700">{rangeStart}–{rangeEnd}</span> of{' '}
        <span className="font-semibold text-surface-700">{totalItems.toLocaleString()}</span>
      </p>

      <div className="flex items-center gap-3 order-1 sm:order-2">
        <Select
          value={String(pageSize) as `${PageSize}`}
          options={PAGE_SIZE_OPTIONS.map((size) => ({
            value: String(size),
            label: `${size} / page`,
          }))}
          onChange={(v) => onPageSizeChange(Number(v) as PageSize)}
          variant="compact"
          aria-label="Items per page"
        />

        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="w-9 h-9 rounded-xl border border-surface-200 bg-surface-0 flex items-center justify-center text-surface-600 hover:bg-surface-50 hover:border-brand-300 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-surface-0 disabled:hover:border-surface-200 transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft size={18} />
          </button>

          <span className="px-3 text-sm font-semibold text-surface-700 min-w-[5rem] text-center">
            {page} / {totalPages}
          </span>

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="w-9 h-9 rounded-xl border border-surface-200 bg-surface-0 flex items-center justify-center text-surface-600 hover:bg-surface-50 hover:border-brand-300 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-surface-0 disabled:hover:border-surface-200 transition-colors"
            aria-label="Next page"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
