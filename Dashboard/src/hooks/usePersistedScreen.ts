import { useCallback, useEffect, useState } from 'react';
import { ScreenId } from '../types';

const SCREEN_PARAM = 'screen';
const TASK_PARAM = 'task';

const VALID_SCREENS: ScreenId[] = ['devices', 'posts', 'tasks', 'schedule', 'settings'];

function readScreenFromUrl(): ScreenId {
  const screen = new URLSearchParams(window.location.search).get(SCREEN_PARAM);
  if (screen && VALID_SCREENS.includes(screen as ScreenId)) {
    return screen as ScreenId;
  }
  return 'devices';
}

export function readHighlightTaskId(): number | null {
  const id = new URLSearchParams(window.location.search).get(TASK_PARAM);
  if (!id) return null;
  const parsed = parseInt(id, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function writeScreenToUrl(screen: ScreenId, taskId?: number) {
  const url = new URL(window.location.href);
  if (screen === 'devices') {
    url.searchParams.delete(SCREEN_PARAM);
  } else {
    url.searchParams.set(SCREEN_PARAM, screen);
  }

  if (screen === 'tasks' && taskId) {
    url.searchParams.set(TASK_PARAM, String(taskId));
  } else {
    url.searchParams.delete(TASK_PARAM);
  }

  window.history.replaceState(null, '', url);
}

export function usePersistedScreen() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>(() => readScreenFromUrl());

  const setScreen = useCallback((screen: ScreenId, taskId?: number) => {
    setCurrentScreen(screen);
    writeScreenToUrl(screen, taskId);
  }, []);

  useEffect(() => {
    const onPopState = () => setCurrentScreen(readScreenFromUrl());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  return { currentScreen, setScreen, highlightTaskId: readHighlightTaskId() };
}
