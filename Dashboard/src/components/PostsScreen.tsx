import { SearchBar } from './SearchBar';
import { Account, Post } from '../types';
import { Eye, Heart, MessageCircle, ExternalLink, Film, Image, BarChart3 } from 'lucide-react';

interface PostsScreenProps {
  accounts: Account[];
  searchCategory: 'username' | 'profile_id' | 'mobile';
  searchQuery: string;
  selectedDevice: Account | null;
  onSearchCategoryChange: (category: 'username' | 'profile_id' | 'mobile') => void;
  onSearchQueryChange: (query: string) => void;
}

interface FlatPost extends Post {
  account: {
    username: string;
    profile_id: string;
    mobile: string;
  };
}

export function PostsScreen({
  accounts,
  searchCategory,
  searchQuery,
  onSearchCategoryChange,
  onSearchQueryChange,
}: PostsScreenProps) {
  const getAllPosts = (): FlatPost[] => {
    return accounts.flatMap((account) =>
      account.posts.map((post) => ({
        ...post,
        account: {
          username: account.username,
          profile_id: account.profile_id,
          mobile: account.mobile,
        },
      }))
    );
  };

  const getFieldValue = (post: FlatPost, category: string): string => {
    if (category === 'username') return post.account.username;
    if (category === 'profile_id') return post.account.profile_id;
    if (category === 'mobile') return post.account.mobile;
    return '';
  };

  const allPosts = getAllPosts();

  const filteredPosts = allPosts
    .filter((post) => {
      if (!searchQuery) return true;
      const fieldValue = getFieldValue(post, searchCategory).toLowerCase();
      return fieldValue.includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => b.stats.views - a.stats.views);

  const formatDate = (timestamp: number): string => {
    const date = new Date(timestamp * 1000);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  };

  const getDisplayUrl = (url: string): string => {
    try {
      const urlObj = new URL(url);
      return urlObj.pathname.replace(/\//g, '');
    } catch {
      return url;
    }
  };

  const getActiveFilterLabel = (): string => {
    if (!searchQuery) {
      return 'Showing all posts';
    }
    const post = filteredPosts[0];
    if (post) {
      const fieldValue = getFieldValue(post, searchCategory);
      return `Showing posts for @${fieldValue} \u00B7 ${post.account.mobile}`;
    }
    return 'Showing all posts';
  };

  const totalViews = filteredPosts.reduce((sum, post) => sum + post.stats.views, 0);
  const totalLikes = filteredPosts.reduce((sum, post) => sum + post.stats.likes, 0);
  const totalComments = filteredPosts.reduce((sum, post) => sum + post.stats.comments, 0);

  return (
    <div className="lg:ml-[272px] min-h-screen bg-surface-50 pt-14 lg:pt-0">
      <div className="px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 tracking-tight">Posts</h1>
          <p className="text-surface-500 mt-1 text-sm">{getActiveFilterLabel()}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6 lg:mb-8 animate-fade-in">
          <div className="bg-surface-0 rounded-xl border border-surface-200/80 p-4 sm:p-5 shadow-card">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
                <Eye size={16} className="text-brand-600 sm:w-[18px] sm:h-[18px]" />
              </div>
              <div>
                <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider">Total Views</p>
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalViews.toLocaleString()}</p>
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
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalLikes.toLocaleString()}</p>
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
                <p className="text-xl sm:text-2xl font-bold text-surface-900">{totalComments.toLocaleString()}</p>
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

        {filteredPosts.length === 0 ? (
          <div className="text-center py-16 sm:py-20 animate-fade-in">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-surface-100 flex items-center justify-center mx-auto mb-4">
              <BarChart3 size={24} className="text-surface-300 sm:w-7 sm:h-7" />
            </div>
            <p className="text-surface-500 text-base font-medium">No posts found.</p>
            <p className="text-surface-400 text-sm mt-1">Try adjusting your search criteria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {filteredPosts.map((post, idx) => (
              <button
                key={`${post.account.profile_id}-${idx}`}
                onClick={() => window.open(post.permalink, '_blank')}
                className="group bg-surface-0 rounded-2xl border border-surface-200/80 p-5 sm:p-6 shadow-card hover:shadow-card-hover hover:border-brand-300 transition-all duration-300 text-left animate-slide-up"
                style={{ animationDelay: `${idx * 40}ms`, animationFillMode: 'both' }}
              >
                <div className="flex items-start justify-between mb-3 sm:mb-4">
                  <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
                    <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      post.stats.media_type === 2 ? 'bg-orange-50' : 'bg-emerald-50'
                    }`}>
                      {post.stats.media_type === 2 ? (
                        <Film size={12} className="text-orange-500 sm:w-3.5 sm:h-3.5" />
                      ) : (
                        <Image size={12} className="text-emerald-500 sm:w-3.5 sm:h-3.5" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs sm:text-sm text-surface-700 font-semibold truncate">
                        @{post.account.username}
                      </p>
                      <p className="text-[11px] sm:text-xs text-surface-400">{post.account.mobile}</p>
                    </div>
                  </div>
                  <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-surface-50 group-hover:bg-brand-50 flex items-center justify-center transition-colors flex-shrink-0">
                    <ExternalLink size={12} className="text-surface-300 group-hover:text-brand-500 transition-colors sm:w-3.5 sm:h-3.5" />
                  </div>
                </div>

                <a
                  href={post.permalink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-600 hover:text-brand-700 text-[11px] sm:text-xs font-mono block mb-3 sm:mb-4 truncate transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  instagram.com/{getDisplayUrl(post.permalink)}
                </a>

                <div className="flex items-center gap-1.5 text-[11px] sm:text-xs text-surface-400 mb-4 sm:mb-5 pb-4 sm:pb-5 border-b border-surface-100">
                  <span>{formatDate(post.stats.timestamp)}</span>
                </div>

                <div className="grid grid-cols-3 gap-2 sm:gap-3">
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Views</p>
                    <div className="flex items-center gap-1">
                      <Eye size={12} className="text-brand-500 sm:w-3.5 sm:h-3.5" />
                      <span className="text-sm sm:text-base font-bold text-surface-900">{post.stats.views.toLocaleString()}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Likes</p>
                    <div className="flex items-center gap-1">
                      <Heart size={12} className="text-rose-500 sm:w-3.5 sm:h-3.5" />
                      <span className="text-sm sm:text-base font-bold text-surface-900">{post.stats.likes.toLocaleString()}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-[11px] text-surface-400 font-medium uppercase tracking-wider mb-1">Comments</p>
                    <div className="flex items-center gap-1">
                      <MessageCircle size={12} className="text-teal-600 sm:w-3.5 sm:h-3.5" />
                      <span className="text-sm sm:text-base font-bold text-surface-900">{post.stats.comments.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
