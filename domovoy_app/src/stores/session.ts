import { defineStore } from 'pinia'
import { client, getHeaders } from '../services/domovoy'
import type { GetHashcashResponse, GetSessionResponse } from '@/services/domovoy/usersV1'
import { useLoadingState } from './manager'
import { ref } from 'vue'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref<string>(window.localStorage.getItem('x-session-key') || '')
  const session = ref<null | GetSessionResponse>(null)
  const { loading, initialized, error, startLoading, finishLoading, setError } = useLoadingState()

  async function reloadSession() {
    startLoading()
    try {
      const result = (await client.GET('/api/users/v1/session', { headers: getHeaders() })).data
      if (!result) throw new Error('No response')
      session.value = result
    } catch (err) {
      setError('Not logged in')
    }
  }

  async function setSessionId(value: string) {
    sessionId.value = value
    window.localStorage.setItem('x-session-key', sessionId.value)
    await reloadSession()
  }

  async function clearSession() {
    session.value = null
    sessionId.value = ''
    await client.DELETE('/api/users/v1/session', { headers: getHeaders() })
    window.localStorage.setItem('x-session-key', '')
  }

  return {
    reloadSession,
    clearSession,
    setSessionId,
    sessionId,
    session
  }
})
