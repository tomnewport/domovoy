import { defineStore } from 'pinia'
import { client, getHeaders } from '../services/domovoy'
import type { GetSessionResponse } from '@/services/domovoy/usersV1'
import { useLoadingState } from './manager'
import { computed, ref } from 'vue'
import { clearCache, readCache, writeCache } from '@/utils/cache'

const SESSION_CACHE_KEY = 'session'
const ONE_HOUR = 60 * 60 * 1000

// A session that expires within the hour is treated as logged out, so nobody
// starts a task and then loses it to an expiry.
function isUsable(session: GetSessionResponse | null): session is GetSessionResponse {
  return !!session && new Date(session.session_expires).getTime() > Date.now() + ONE_HOUR
}

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref<string>(window.localStorage.getItem('x-session-key') || '')
  // The last session the server confirmed for this key. Starting from it lets a
  // returning user see the app at once while the session is re-checked.
  const cached = sessionId.value ? readCache<GetSessionResponse>(SESSION_CACHE_KEY) : null
  const session = ref<null | GetSessionResponse>(isUsable(cached) ? cached : null)
  const { loading, initialized, error, startLoading, finishLoading, setError } = useLoadingState()

  const loggedIn = computed(() => isUsable(session.value))
  // There is a key to check but no answer (or cached session) yet: show a
  // splash rather than flashing the login form at someone who is logged in.
  const checking = computed(() => !!sessionId.value && !session.value && !initialized.value)

  async function reloadSession() {
    if (!sessionId.value) {
      session.value = null
      finishLoading()
      return
    }
    startLoading()
    try {
      const { data, response } = await client.GET('/api/users/v1/session', {
        headers: getHeaders()
      })
      if (data) {
        session.value = data
        writeCache(SESSION_CACHE_KEY, data)
      } else if (response.status === 401 || response.status === 403) {
        session.value = null
        clearCache()
      }
      // Any other failure (5xx, offline) keeps the session we already had.
      finishLoading()
    } catch {
      setError('Could not check your session')
      initialized.value = true
    }
  }

  async function setSessionId(value: string) {
    sessionId.value = value
    window.localStorage.setItem('x-session-key', sessionId.value)
    await reloadSession()
  }

  async function clearSession() {
    await client.DELETE('/api/users/v1/session', { headers: getHeaders() })
    session.value = null
    sessionId.value = ''
    window.localStorage.setItem('x-session-key', '')
    clearCache()
  }

  return {
    reloadSession,
    clearSession,
    setSessionId,
    sessionId,
    session,
    loggedIn,
    checking,
    loading,
    error
  }
})
