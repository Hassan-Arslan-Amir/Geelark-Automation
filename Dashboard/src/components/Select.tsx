import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

interface SelectProps<T extends string> {
  id?: string;
  value: T;
  options: SelectOption<T>[];
  onChange: (value: T) => void;
  variant?: 'default' | 'compact' | 'attached-left';
  className?: string;
  'aria-label'?: string;
}

const triggerVariants = {
  default:
    'w-full px-4 py-3 rounded-xl border border-surface-200 bg-surface-0 text-sm',
  compact:
    'px-3 py-2 rounded-xl border border-surface-200 bg-surface-0 text-sm',
  'attached-left':
    'h-full min-w-[7.5rem] pl-4 pr-3 rounded-l-xl border border-r-0 border-surface-200 bg-surface-0 text-sm',
};

export function Select<T extends string>({
  id,
  value,
  options,
  onChange,
  variant = 'default',
  className = '',
  'aria-label': ariaLabel,
}: SelectProps<T>) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleSelect = (next: T) => {
    onChange(next);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className={`relative ${variant === 'default' ? 'w-full' : ''} ${className}`}>
      <button
        id={id}
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={`group flex items-center justify-between gap-3 text-left font-semibold text-surface-700 transition-all duration-200 hover:bg-surface-50 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 ${
          open ? 'ring-2 ring-brand-500/20 border-brand-400 bg-surface-50' : ''
        } ${triggerVariants[variant]}`}
      >
        <span className="truncate">{selected?.label ?? 'Select…'}</span>
        <span
          className={`flex-shrink-0 flex items-center justify-center rounded-lg bg-surface-100 text-surface-500 transition-all duration-200 group-hover:bg-surface-200 group-hover:text-surface-600 ${
            variant === 'compact' ? 'w-6 h-6' : 'w-7 h-7'
          } ${open ? 'bg-brand-50 text-brand-600 rotate-180' : ''}`}
        >
          <ChevronDown size={variant === 'compact' ? 14 : 16} strokeWidth={2.2} />
        </span>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={ariaLabel}
          className="absolute z-50 mt-1.5 w-full min-w-[10rem] overflow-hidden rounded-xl border border-surface-200/80 bg-surface-0 py-1.5 shadow-card-hover animate-scale-in origin-top"
        >
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <li key={option.value} role="option" aria-selected={isSelected}>
                <button
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className={`w-full flex items-center justify-between gap-2 px-3.5 py-2.5 text-left text-sm transition-colors ${
                    isSelected
                      ? 'bg-brand-50 text-brand-700 font-semibold'
                      : 'text-surface-700 font-medium hover:bg-surface-50'
                  }`}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && (
                    <Check size={15} className="text-brand-600 flex-shrink-0" strokeWidth={2.5} />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
