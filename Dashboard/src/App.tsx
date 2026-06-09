import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { DevicesScreen } from './components/DevicesScreen';
import { PostsScreen } from './components/PostsScreen';
import { SchedulePostScreen } from './components/SchedulePostScreen';
import { Account, ScreenId } from './types';
import { useSupabaseData } from './hooks/useSupabaseData';

function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('devices');
  const [selectedDevice, setSelectedDevice] = useState<Account | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [devicesSearchCategory, setDevicesSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [devicesSearchQuery, setDevicesSearchQuery] = useState('');

  const [postsSearchCategory, setPostsSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [postsSearchQuery, setPostsSearchQuery] = useState('');

  const { data: analyticsData, loading, error } = useSupabaseData();

  const handleDeviceClick = (account: Account) => {
    setSelectedDevice(account);
    setPostsSearchQuery(account.username);
    setPostsSearchCategory('username');
    setCurrentScreen('posts');
  };

  const handleNavigate = (screen: ScreenId) => {
    if (screen === 'devices') {
      setSelectedDevice(null);
      setPostsSearchQuery('');
    } else if (screen === 'posts' && !selectedDevice) {
      setPostsSearchQuery('');
      setPostsSearchCategory('username');
    }
    setCurrentScreen(screen);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface-50">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-surface-500 text-sm font-medium">Loading data from Supabase…</p>
        </div>
      </div>
    );
  }

  if (error || !analyticsData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface-50">
        <div className="text-center max-w-sm px-6">
          <p className="text-red-500 font-semibold text-base mb-2">Failed to load data</p>
          <p className="text-surface-400 text-sm">{error ?? 'Unknown error'}</p>
          <p className="text-surface-400 text-xs mt-3">Check that VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in Dashboard/.env</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex">
      <Sidebar
        currentScreen={currentScreen}
        onNavigate={handleNavigate}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {currentScreen === 'devices' && (
        <DevicesScreen
          accounts={analyticsData.accounts}
          searchCategory={devicesSearchCategory}
          searchQuery={devicesSearchQuery}
          onSearchCategoryChange={setDevicesSearchCategory}
          onSearchQueryChange={setDevicesSearchQuery}
          onDeviceClick={handleDeviceClick}
        />
      )}

      {currentScreen === 'posts' && (
        <PostsScreen
          accounts={analyticsData.accounts}
          searchCategory={postsSearchCategory}
          searchQuery={postsSearchQuery}
          selectedDevice={selectedDevice}
          onSearchCategoryChange={setPostsSearchCategory}
          onSearchQueryChange={setPostsSearchQuery}
        />
      )}

      {currentScreen === 'schedule' && (
        <SchedulePostScreen accounts={analyticsData.accounts} />
      )}
    </div>
  );
}

export default App;
