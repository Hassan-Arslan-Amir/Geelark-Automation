import { Smartphone, BarChart3, X, Menu } from 'lucide-react';

interface SidebarProps {
  currentScreen: 'devices' | 'posts';
  onNavigate: (screen: 'devices' | 'posts') => void;
  isOpen: boolean;
  onToggle: () => void;
}

export function Sidebar({ currentScreen, onNavigate, isOpen, onToggle }: SidebarProps) {
  const items = [
    { id: 'devices', label: 'Devices', icon: Smartphone },
    { id: 'posts', label: 'Posts', icon: BarChart3 },
  ];

  const handleNav = (screen: 'devices' | 'posts') => {
    onNavigate(screen);
    if (window.innerWidth < 1024) {
      onToggle();
    }
  };

  return (
    <>
      {/* Mobile header bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-surface-950 z-50 flex items-center justify-between px-4 shadow-sidebar">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center overflow-hidden">
            <img src="/assets/browser_icon_2.png" alt="Analytics" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-base font-bold text-white tracking-tight">Analytics</h1>
        </div>
        <button
          onClick={onToggle}
          className="w-9 h-9 rounded-lg bg-surface-800 flex items-center justify-center hover:bg-surface-700 transition-colors"
        >
          {isOpen ? <X size={18} className="text-white" /> : <Menu size={18} className="text-white" />}
        </button>
      </div>

      {/* Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
          onClick={onToggle}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 left-0 h-full bg-surface-950 text-white flex flex-col shadow-sidebar z-50 transition-transform duration-300 ease-in-out w-[272px]
          ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0
        `}
      >
        <div className="px-6 pt-8 pb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg from-brand-500 to-brand-700 flex items-center justify-center overflow-hidden">
              <img src="/assets/browser_icon_2.png" alt="Analytics" className="w-full h-full object-cover" />
          </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Analytics</h1>
              <p className="text-[11px] text-surface-400 font-medium tracking-wider uppercase">Dashboard</p>
            </div>
          </div>
        </div>

        <div className="px-4 mb-2">
          <div className="h-px bg-surface-800" />
        </div>

        <nav className="flex-1 px-3">
          <p className="text-[11px] text-surface-500 font-semibold tracking-wider uppercase px-3 mb-2">Navigation</p>
          <ul className="space-y-1">
            {items.map(({ id, label, icon: Icon }) => (
              <li key={id}>
                <button
                  onClick={() => handleNav(id as 'devices' | 'posts')}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    currentScreen === id
                      ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/25'
                      : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/60'
                  }`}
                >
                  <Icon size={18} strokeWidth={currentScreen === id ? 2.2 : 1.8} />
                  <span>{label}</span>
                  {currentScreen === id && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white/80" />
                  )}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* <div className="px-4 pb-4">
          <div className="h-px bg-surface-800 mb-4" />
          <div className="px-3 py-3 rounded-lg bg-surface-900/60 border border-surface-800/50">
            <p className="text-[11px] text-surface-500 font-medium">Data refreshed</p>
            <p className="text-xs text-surface-300 font-medium mt-0.5">May 19, 2026</p>
          </div>
        </div> */}
      </aside>
    </>
  );
}
