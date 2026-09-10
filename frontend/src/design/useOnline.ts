import { useEffect, useState } from 'react';

/**
 * useOnline — the browser's connectivity signal. The app bar always shows a
 * connectivity indicator (Phase 4 §6.5). A richer syncing / sync-issue state
 * belongs to the offline/outbox work in a later phase; this reports the one
 * signal the platform gives us today.
 */
export function useOnline(): boolean {
  const [online, setOnline] = useState<boolean>(() =>
    typeof navigator === 'undefined' ? true : navigator.onLine,
  );
  useEffect(() => {
    const up = (): void => setOnline(true);
    const down = (): void => setOnline(false);
    window.addEventListener('online', up);
    window.addEventListener('offline', down);
    return () => {
      window.removeEventListener('online', up);
      window.removeEventListener('offline', down);
    };
  }, []);
  return online;
}
