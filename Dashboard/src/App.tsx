import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { DevicesScreen } from './components/DevicesScreen';
import { PostsScreen } from './components/PostsScreen';
import { AnalyticsData, Account } from './types';
import data from './data.json';

function App() {
  const [currentScreen, setCurrentScreen] = useState<'devices' | 'posts'>('devices');
  const [selectedDevice, setSelectedDevice] = useState<Account | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [devicesSearchCategory, setDevicesSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [devicesSearchQuery, setDevicesSearchQuery] = useState('');

  const [postsSearchCategory, setPostsSearchCategory] = useState<'username' | 'profile_id' | 'mobile'>('username');
  const [postsSearchQuery, setPostsSearchQuery] = useState('');

  const analyticsData = data as AnalyticsData;

  const handleDeviceClick = (account: Account) => {
    setSelectedDevice(account);
    setPostsSearchQuery(account.username);
    setPostsSearchCategory('username');
    setCurrentScreen('posts');
  };

  const handleNavigate = (screen: 'devices' | 'posts') => {
    if (screen === 'devices') {
      setSelectedDevice(null);
      setPostsSearchQuery('');
    } else if (screen === 'posts' && !selectedDevice) {
      setPostsSearchQuery('');
      setPostsSearchCategory('username');
    }
    setCurrentScreen(screen);
  };

  return (
    <div className="flex">
      <Sidebar
        currentScreen={currentScreen}
        onNavigate={handleNavigate}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {currentScreen === 'devices' ? (
        <DevicesScreen
          accounts={analyticsData.accounts}
          searchCategory={devicesSearchCategory}
          searchQuery={devicesSearchQuery}
          onSearchCategoryChange={setDevicesSearchCategory}
          onSearchQueryChange={setDevicesSearchQuery}
          onDeviceClick={handleDeviceClick}
        />
      ) : (
        <PostsScreen
          accounts={analyticsData.accounts}
          searchCategory={postsSearchCategory}
          searchQuery={postsSearchQuery}
          selectedDevice={selectedDevice}
          onSearchCategoryChange={setPostsSearchCategory}
          onSearchQueryChange={setPostsSearchQuery}
        />
      )}
    </div>
  );
}

export default App;
