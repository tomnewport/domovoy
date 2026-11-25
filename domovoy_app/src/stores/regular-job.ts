import { defineStore } from 'pinia'
import type { components } from '@/services/domovoy/schema.d.ts'
import { computed, ref } from 'vue'
import { useLoadingState } from './manager'
import { client, getHeaders } from '@/services/domovoy'
import { useSessionStore } from './session'
import { readCache, writeCache } from '@/utils/cache'

export type RegularJobDefinition = components['schemas']['RegularJobDefinitionSchema']
export type HomeStatistics = components['schemas']['HomeStatistics']
export type ClaimResponse = components['schemas']['ClaimResponse']
export type RuleComputeResult = components['schemas']['RuleComputeResult']
export type SnoozeOption = components['schemas']['SnoozeOption']
export type Ruleset = components['schemas']['Ruleset']
export type RuleCalendar = components['schemas']['RuleCalendar']
export type RuleDelay = components['schemas']['RuleDelay']

export type EditJobDefinition = components['schemas']['RegularJobDefinitionEditSchema']

export interface Motivation {
  open: boolean
  valueChange: number
  stats: HomeStatistics
  result: RuleComputeResult | null
}

export interface SnoozeOptionsState {
  options: SnoozeOption[] | null
  error: boolean
}

// Snooze dates depend on the job's current due date, so a cached answer is only
// reused while that date is unchanged.
function snoozeKey(job: RegularJobDefinition) {
  return `${job.id}:${job.next_assigned_due_date}`
}

export const useRegularJobStore = defineStore('regular-job', () => {
  const sessionStore = useSessionStore()
  const cacheKey = () => (sessionStore.session ? `definitions:${sessionStore.session.id}` : null)

  // Start from the jobs this user saw last time, so the list draws at once.
  // `fresh` (below) says whether the server has confirmed them in this visit.
  const startKey = cacheKey()
  const definitions = ref<RegularJobDefinition[]>(
    (startKey && readCache<RegularJobDefinition[]>(startKey)) || []
  )
  const loadingState = useLoadingState()
  const fresh = computed(() => loadingState.initialized.value)
  const hasData = computed(() => fresh.value || definitions.value.length > 0)

  async function editDefinition(definitionId: number, changes: Partial<EditJobDefinition>) {
    const result = await client.PATCH('/api/regular_jobs/v1/definitions/{definition_id}', {
      headers: getHeaders(),
      params: {
        path: { definition_id: definitionId }
      },
      body: changes as EditJobDefinition
    })
    if (result.data) {
      const unchanged = definitions.value.filter((def) => def.id !== definitionId)
      definitions.value = [...unchanged, result.data]
    }
  }

  // One request per scope at a time: the app shell, the task list and the job
  // editor all ask for the same list as the app opens.
  const inFlight = new Map<string, Promise<void>>()

  function reload({ homeId }: { homeId?: number } = {}): Promise<void> {
    const scope = homeId === undefined ? 'all' : `home:${homeId}`
    const existing = inFlight.get(scope)
    if (existing) return existing
    const request = (async () => {
      if (homeId === undefined) loadingState.startLoading()
      try {
        const result = await client.GET('/api/regular_jobs/v1/definitions', {
          headers: getHeaders(),
          params: {
            query: {
              home_id: homeId
            }
          }
        })
        const isReplaced = (definition: RegularJobDefinition): boolean =>
          homeId ? homeId === definition.home : true
        if (result.data) {
          const unchanged = definitions.value.filter((def) => !isReplaced(def))
          definitions.value = [...unchanged, ...result.data]
          if (homeId === undefined) {
            const key = cacheKey()
            if (key) writeCache(key, result.data)
            loadingState.finishLoading()
          }
        } else if (homeId === undefined) {
          loadingState.setError('Could not load your tasks')
        }
      } catch {
        if (homeId === undefined) loadingState.setError('Could not load your tasks')
      } finally {
        inFlight.delete(scope)
      }
    })()
    inFlight.set(scope, request)
    return request
  }

  async function claim({ definitionId, value }: { definitionId: number; value?: number }) {
    const result = await client.POST('/api/regular_jobs/v1/definitions/{definition_id}/instances', {
      headers: getHeaders(),
      params: { path: { definition_id: definitionId } },
      body: { value }
    })
    if (!result.data) throw new Error('Could not claim this job')
    motivation.value = {
      open: true,
      valueChange: result.data.value,
      stats: result.data.statistics,
      result: result.data.result
    }
    // Refresh in the background: the congratulations dialog is already up.
    void reload()
  }

  const snoozeOptions = ref<Record<string, SnoozeOptionsState>>({})
  const snoozeRequests = new Map<string, Promise<void>>()

  // Fetch a job's snooze dates ahead of time (when its card opens), so the
  // menu has them ready by the time someone taps "Snooze".
  function prefetchSnoozeOptions(job: RegularJobDefinition): Promise<void> {
    if (!job.id) return Promise.resolve()
    const key = snoozeKey(job)
    const pending = snoozeRequests.get(key)
    if (pending) return pending
    if (snoozeOptions.value[key]?.options) return Promise.resolve()
    const request = (async () => {
      snoozeOptions.value[key] = { options: null, error: false }
      try {
        const result = await client.GET('/api/regular_jobs/v1/definitions/{definition_id}/snooze', {
          headers: getHeaders(),
          params: { path: { definition_id: job.id as number } }
        })
        snoozeOptions.value[key] = result.data
          ? { options: result.data, error: false }
          : { options: null, error: true }
      } catch {
        snoozeOptions.value[key] = { options: null, error: true }
      } finally {
        snoozeRequests.delete(key)
      }
    })()
    snoozeRequests.set(key, request)
    return request
  }

  function snoozeOptionsFor(job: RegularJobDefinition): SnoozeOptionsState | undefined {
    return snoozeOptions.value[snoozeKey(job)]
  }

  async function snooze(jobId: number, date: string) {
    const result = await client.POST('/api/regular_jobs/v1/definitions/{definition_id}/snooze', {
      headers: getHeaders(),
      params: {
        path: { definition_id: jobId },
        query: { new_date: date }
      }
    })
    if (result.error) throw new Error('Could not snooze this job')
    void reload()
  }

  const motivation = ref<null | Motivation>(null)

  function closeMotivation() {
    motivation.value = null
  }

  return {
    prefetchSnoozeOptions,
    snoozeOptionsFor,
    motivation,
    closeMotivation,
    definitions,
    editDefinition,
    reload,
    loadingState,
    loading: loadingState.loading,
    fresh,
    hasData,
    claim,
    snooze
  }
})
