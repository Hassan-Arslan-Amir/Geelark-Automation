import { Search } from 'lucide-react';
import { Select } from './Select';

interface SearchBarProps {
  category: 'username' | 'profile_id' | 'mobile';
  query: string;
  onCategoryChange: (category: 'username' | 'profile_id' | 'mobile') => void;
  onQueryChange: (query: string) => void;
}

export function SearchBar({
  category,
  query,
  onCategoryChange,
  onQueryChange,
}: SearchBarProps) {
  const categories = [
    { value: 'username' as const, label: 'Username' },
    { value: 'profile_id' as const, label: 'Profile ID' },
    { value: 'mobile' as const, label: 'Mobile' },
  ];

  return (
    <div className="flex items-stretch">
      <Select
        value={category}
        options={categories}
        onChange={onCategoryChange}
        variant="attached-left"
        aria-label="Search category"
      />

      <div className="relative flex-1">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-surface-400" size={18} />
        <input
          type="text"
          placeholder="Type to search..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className="w-full h-full pl-11 pr-4 py-3 border border-surface-200 rounded-r-xl bg-surface-0 text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 transition-all"
        />
        {query && (
          <button
            onClick={() => onQueryChange('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-surface-200 hover:bg-surface-300 flex items-center justify-center transition-colors"
          >
            <span className="text-surface-600 text-xs leading-none">&times;</span>
          </button>
        )}
      </div>
    </div>
  );
}
