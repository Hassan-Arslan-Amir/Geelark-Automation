export type Platform = 'instagram' | 'tiktok' | 'facebook' | 'youtube';
export type MediaType = 'video' | 'image';

export const PLATFORM_OPTIONS: {
  value: Platform;
  label: string;
  supports: MediaType[];
}[] = [
  { value: 'instagram', label: 'Instagram', supports: ['video', 'image'] },
  { value: 'tiktok', label: 'TikTok', supports: ['video', 'image'] },
  { value: 'facebook', label: 'Facebook', supports: ['video'] },
  { value: 'youtube', label: 'YouTube', supports: ['video'] },
];

export function getMediaTypesForPlatform(platform: Platform): MediaType[] {
  return PLATFORM_OPTIONS.find((p) => p.value === platform)?.supports ?? ['video'];
}
