import { HelpCircle } from 'lucide-react';

interface FieldHelpProps {
  text: string;
}

export function FieldHelp({ text }: FieldHelpProps) {
  return (
    <span className="relative inline-flex group/help align-middle ml-1.5">
      <button
        type="button"
        tabIndex={0}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full text-surface-400 hover:text-brand-600 hover:bg-brand-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"
        aria-label="Field help"
      >
        <HelpCircle size={14} />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 bottom-full z-50 mb-2 w-64 -translate-x-1/2 rounded-xl border border-surface-200 bg-surface-900 px-3 py-2.5 text-xs font-normal normal-case tracking-normal text-white leading-relaxed opacity-0 shadow-lg transition-opacity duration-150 group-hover/help:opacity-100 group-focus-within/help:opacity-100"
      >
        {text}
        <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-surface-900" />
      </span>
    </span>
  );
}
