import { useCallback, useEffect, useRef, useState } from 'react';
import { ScheduledTask } from '../types';
import { fetchScheduledTasks, deleteScheduledTask } from './useSchedulePost';

const POLL_INTERVAL_MS = 10_000;

export function useScheduledTasks() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const hasLoadedRef = useRef(false);

  const refetch = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? hasLoadedRef.current;

    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
      setError(null);
    }

    try {
      const data = await fetchScheduledTasks();
      setTasks(data);
      if (!silent) setError(null);
      hasLoadedRef.current = true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load tasks.';
      if (!silent || !hasLoadedRef.current) {
        setError(message);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const deleteTask = useCallback(async (id: number) => {
    setDeletingId(id);
    setError(null);
    try {
      await deleteScheduledTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete task.';
      setError(message);
      throw err;
    } finally {
      setDeletingId(null);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      refetch({ silent: true });
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [refetch]);

  const clearError = useCallback(() => setError(null), []);

  return { tasks, loading, refreshing, error, deletingId, refetch, deleteTask, clearError };
}
