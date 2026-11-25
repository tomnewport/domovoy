// The server's reason for refusing a request, when it gave one in words
// (django-ninja's `{"detail": "..."}`); otherwise `fallback`.
export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  return typeof detail === 'string' ? detail : fallback
}
