// Per-device settings, kept in localStorage. Unlike utils/cache.ts these
// survive logging out. Best-effort: with storage unavailable, the default
// is used and changes last until the page is reloaded.

const PREFIX = 'domovoy-pref:'

export function readPreference<T extends string>(
  key: string,
  allowed: readonly T[],
  fallback: T
): T {
  try {
    const value = window.localStorage.getItem(PREFIX + key)
    return allowed.includes(value as T) ? (value as T) : fallback
  } catch {
    return fallback
  }
}

export function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(PREFIX + key, value)
  } catch {
    // Storage unavailable: the choice holds for this visit only.
  }
}
