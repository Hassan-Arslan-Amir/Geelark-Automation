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

export type ScreenId = 'devices' | 'posts' | 'tasks' | 'schedule' | 'settings';

export interface BotSettings {
  google_drive_url: string;
  openai_api_key: string;
  geelark_app_id: string;
  geelark_api_key: string;
  geelark_bearer_token: string;
}

export type ScheduleMode = 'auto' | 'manual';

/** How many calendar days the task repeats (1 = single day, 7 = week, 30 = month). */
export type ScheduleDuration = 'day' | 'week' | 'month';

export interface ScheduledTaskPayload {
  platform: string;
  media_type: string;
  content_count: number;
  device_ids: Record<string, string>;
  schedule_mode: ScheduleMode;
  schedule_duration: ScheduleDuration;
  schedule_times: string[] | null;
  caption_enabled: boolean;
  caption_prompt: string | null;
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'posted' | 'failed';

export interface ScheduledTask {
  id: number;
  platform: string;
  media_type: string;
  content_count: number;
  device_ids: Record<string, string>;
  schedule_mode: ScheduleMode;
  schedule_duration: ScheduleDuration;
  schedule_times: string[] | null;
  schedule_at: string | null;
  posts_completed: number;
  caption_enabled: boolean;
  caption_prompt: string | null;
  status: TaskStatus;
  error: string | null;
  created_at: string;
}
