// A small localStorage cache so the app can draw the last-known data at once
// and refresh it in the background (stale-while-revalidate). Everything here is
// best-effort: storage can be full, disabled or cleared, so reads fall back to
// null and writes are dropped silently.

const PREFIX = 'domovoy-cache:'

export function readCache<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(PREFIX + key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function writeCache<T>(key: string, value: T): void {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    // Quota exceeded or storage unavailable: the cache is only an optimisation.
  }
}

export function clearCache(): void {
  try {
    Object.keys(window.localStorage)
      .filter((key) => key.startsWith(PREFIX))
      .forEach((key) => window.localStorage.removeItem(key))
  } catch {
    // Nothing to clear.
  }
}
