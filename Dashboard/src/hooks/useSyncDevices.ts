export interface SyncDevicesResult {
  ok: boolean;
  fetched_from_geelark?: number;
  total_in_json?: number;
  updated_entries?: number;
  message?: string;
  error?: string;
}

export async function syncDevicesFromGeelark(): Promise<SyncDevicesResult> {
  const base = import.meta.env.VITE_API_URL ?? '';
  const response = await fetch(`${base}/api/sync-devices`, { method: 'POST' });

  const data = (await response.json()) as SyncDevicesResult;

  if (!response.ok || !data.ok) {
    throw new Error(data.error ?? 'Failed to sync devices from GeeLark.');
  }

  return data;
}
