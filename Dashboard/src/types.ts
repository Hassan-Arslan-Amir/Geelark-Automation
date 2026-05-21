export interface Stats {
  views: number;
  likes: number;
  comments: number;
  reshares: number;
  media_type: number;
  timestamp: number;
  reach: number;
  impressions: number;
  saves: number;
}

export interface Post {
  permalink: string;
  stats: Stats;
}

export interface Account {
  profile_id: string;
  mobile: string;
  username: string;
  posts: Post[];
}

export interface AnalyticsData {
  fetched_at: string;
  total_devices: number;
  aggregate: {
    total_views: number;
    total_likes: number;
    total_comments: number;
  };
  accounts: Account[];
}
