import { defineStore } from 'pinia'
import type { components } from '@/services/domovoy/schema'
import { ref } from 'vue'
import { useLoadingState } from './manager'
import { client, getHeaders } from '@/services/domovoy'

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
  result: RuleComputeResult
}

export const useRegularJobStore = defineStore('regular-job', () => {
  const definitions = ref<RegularJobDefinition[]>([])
  const loadingState = useLoadingState()

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

  async function reload({ homeId }: { homeId?: number } = {}) {
    const result = await client.GET('/api/regular_jobs/v1/definitions', {
      headers: getHeaders(),
      params: {
        query: {
          home_id: homeId
        }
      }
    })
    function isReplaced(definition: RegularJobDefinition): Boolean {
      if (homeId) {
        return homeId === definition.home
      }
      return true
    }
    if (result.data) {
      const unchanged = definitions.value.filter((def) => !isReplaced(def))
      definitions.value = [...unchanged, ...result.data]
    }
  }

  async function claim({ definitionId, value }: { definitionId: number; value?: number }) {
    const result = await client.POST('/api/regular_jobs/v1/definitions/{definition_id}/instances', {
      headers: getHeaders(),
      params: { path: { definition_id: definitionId } },
      body: { value }
    })
    if (result.data) {
      motivation.value = {
        open: true,
        valueChange: result.data.value,
        stats: result.data.statistics,
        result: result.data.result
      }
    }
    await reload()
  }

  async function loadSnoozeOptions(jobId: number) {
    snoozeOptions.value = []
    const result = await client.GET('/api/regular_jobs/v1/definitions/{definition_id}/snooze', {
      headers: getHeaders(),
      params: { path: { definition_id: jobId } }
    })
    if (result.data) snoozeOptions.value = result.data
  }

  async function snooze(jobId: number, date: string) {
    await client.POST('/api/regular_jobs/v1/definitions/{definition_id}/snooze', {
      headers: getHeaders(),
      params: {
        path: { definition_id: jobId },
        query: { new_date: date }
      }
    })
    await reload()
  }

  const motivation = ref<null | Motivation>(null)

  function closeMotivation() {
    motivation.value = null
  }
  const snoozeOptions = ref<SnoozeOption[]>([])

  return {
    loadSnoozeOptions,
    motivation,
    closeMotivation,
    definitions,
    editDefinition,
    reload,
    loadingState,
    claim,
    snoozeOptions,
    snooze
  }
})
