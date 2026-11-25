import { defineStore } from 'pinia'
import { useLoadingState } from './manager'
import { client } from '@/services/domovoy'
import { ref } from 'vue'
import { getHeaders } from '@/services/domovoy/base'
import type { components } from '@/services/domovoy/schema.d.ts'
import { useSessionStore } from './session'
import { readCache, writeCache } from '@/utils/cache'

type Home = components['schemas']['HomeSchema']

export const useHomesStore = defineStore('homes', () => {
  const sessionStore = useSessionStore()
  const { loading, initialized, error, startLoading, finishLoading, setError } = useLoadingState()
  const cacheKey = () => (sessionStore.session ? `homes:${sessionStore.session.id}` : null)

  // Start from the last homes seen by this user, if any; `initialized` only
  // becomes true once the server has answered in this visit.
  const startKey = cacheKey()
  const homes = ref<null | Home[]>(startKey ? readCache<Home[]>(startKey) : null)

  let inFlight: Promise<void> | null = null

  function reloadHomes(): Promise<void> {
    // Several components ask at once on start-up; share one request.
    if (inFlight) return inFlight
    inFlight = (async () => {
      startLoading()
      try {
        const { data } = await client.GET('/api/homes/v1/homes', { headers: getHeaders() })
        if (data) {
          homes.value = data
          const key = cacheKey()
          if (key) writeCache(key, data)
          finishLoading()
        } else {
          setError('Could not fetch homes')
        }
      } catch {
        setError('Could not fetch homes')
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  async function ensureLoaded() {
    if (!initialized.value) await reloadHomes()
  }

  return {
    ensureLoaded,
    homes,
    initialized,
    loading,
    error,
    reloadHomes
  }
})
