import { defineStore } from 'pinia'
import { useLoadingState } from './manager'
import { client } from '@/services/domovoy'
import { ref } from 'vue'
import { getHeaders } from '@/services/domovoy/base'
import type { components } from '@/services/domovoy/schema'

export const useHomesStore = defineStore('homes', () => {
  const { loading, initialized, error, startLoading, finishLoading, setError } = useLoadingState()
  const homes = ref<null | components['schemas']['HomeSchema'][]>(null)
  async function reloadHomes() {
    startLoading()
    const { data, error, response } = await client.GET('/api/homes/v1/homes', {
      headers: getHeaders()
    })
    if (error) {
      setError('Could not fetch homes')
    } else {
      homes.value = data
    }
    while (true) {
      const resolver = waiters.pop()
      if (!resolver) break
      resolver()
    }
    finishLoading()
  }
  const waiters: CallableFunction[] = []
  function ensureLoaded() {
    if (!initialized.value && !loading.value) reloadHomes()
    else if (!loading.value) return true
    return new Promise((resolve) => {
      waiters.push(resolve)
    })
  }
  return {
    ensureLoaded,
    homes,
    initialized,
    loading,
    reloadHomes
  }
})
