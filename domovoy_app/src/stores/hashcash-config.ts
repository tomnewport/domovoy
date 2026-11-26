import { defineStore } from 'pinia'
import API from '../services/domovoy'
import type { GetHashcashResponse } from '@/services/domovoy/usersV1'
import { useLoadingState } from './manager'
import { ref } from 'vue'

export const useHashcashConfigStore = defineStore('hashcashConfig', () => {
  const hashcashConfig = ref<GetHashcashResponse | null>(null)
  const { loading, initialized, error, startLoading, finishLoading, setError } = useLoadingState()
  async function load() {
    startLoading()
    try {
      hashcashConfig.value = (await API.usersV1.getHashcash()).data
      finishLoading()
    } catch {
      setError('Could not load hashcash')
    }
  }
  return {
    load,
    loading,
    initialized,
    error,
    hashcashConfig
  }
})
