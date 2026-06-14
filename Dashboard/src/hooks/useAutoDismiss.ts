import { useEffect } from 'react';

export const FLASH_MESSAGE_DURATION_MS = 30_000;

/** Clears a transient banner/message automatically after the given duration. */
export function useAutoDismiss(
  active: unknown,
  onDismiss: () => void,
  durationMs: number = FLASH_MESSAGE_DURATION_MS,
) {
  useEffect(() => {
    if (active == null || active === false || active === '') return;

    const timer = window.setTimeout(onDismiss, durationMs);
    return () => window.clearTimeout(timer);
  }, [active, onDismiss, durationMs]);
}
