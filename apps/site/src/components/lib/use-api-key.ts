import { useCallback, useEffect, useState } from 'react';

/**
 * The viewer's own API key. Kept in localStorage in the viewer's browser and sent only to
 * the provider endpoint the viewer chose. It is never proxied through this site, never
 * written to any log, and never leaves the browser in any other direction.
 *
 * The site collects no student data of any kind; this hook is the only place any viewer
 * input is persisted at all, and it is persisted locally.
 */
const STORAGE_PREFIX = 'course.playground.';

export function useLocalSetting(key: string, fallback = ''): {
  value: string;
  setValue: (next: string) => void;
  clear: () => void;
  ready: boolean;
} {
  const storageKey = `${STORAGE_PREFIX}${key}`;
  const [value, setValueState] = useState<string>(fallback);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored !== null) setValueState(stored);
    } catch {
      // Private windows and blocked site data both throw. Fall back to in-memory only.
    }
    setReady(true);
  }, [storageKey]);

  const setValue = useCallback(
    (next: string) => {
      setValueState(next);
      try {
        window.localStorage.setItem(storageKey, next);
      } catch {
        /* in-memory only */
      }
    },
    [storageKey],
  );

  const clear = useCallback(() => {
    setValueState(fallback);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      /* in-memory only */
    }
  }, [storageKey, fallback]);

  return { value, setValue, clear, ready };
}
