import { client, getHeaders } from '.'
import type { components } from './schema.d.ts'

export type HomeStatistics = components['schemas']['HomeStatistics']
export type JobCompletion = components['schemas']['JobCompletionSchema']

// Points per member per day for one home, over the last `days` days.
export async function fetchStatistics(homeId: number, days: number): Promise<HomeStatistics> {
  const { data } = await client.GET('/api/regular_jobs/v1/statistics', {
    headers: getHeaders(),
    params: { query: { home_id: homeId, days } }
  })
  if (!data) throw new Error('Could not load statistics')
  return data
}

export interface CompletionQuery {
  homeId?: number
  userId?: number
  since?: Date
  before?: string
  limit?: number
}

// One page of completed jobs, newest first.
export async function fetchCompletions(query: CompletionQuery = {}): Promise<JobCompletion[]> {
  const { data } = await client.GET('/api/regular_jobs/v1/instances', {
    headers: getHeaders(),
    params: {
      query: {
        home_id: query.homeId,
        user_id: query.userId,
        since: query.since?.toISOString(),
        before: query.before,
        limit: query.limit ?? 30
      }
    }
  })
  if (!data) throw new Error('Could not load activity')
  return data
}

// Every completion since `since`, following pages (up to `cap` items).
export async function fetchAllCompletions(
  query: Omit<CompletionQuery, 'before' | 'limit'>,
  cap = 500
): Promise<JobCompletion[]> {
  const all: JobCompletion[] = []
  let before: string | undefined
  while (all.length < cap) {
    const page = await fetchCompletions({ ...query, before, limit: 100 })
    all.push(...page)
    if (page.length < 100) break
    before = page[page.length - 1].completed_at
  }
  return all
}

export type HomeUpkeep = components['schemas']['HomeUpkeep']

// Ideal points per week for one home, and points actually earned per day
// (without overdue bonuses) over the last `days` days.
export async function fetchUpkeep(homeId: number, days = 56): Promise<HomeUpkeep> {
  const { data } = await client.GET('/api/regular_jobs/v1/upkeep', {
    headers: getHeaders(),
    params: { query: { home_id: homeId, days } }
  })
  if (!data) throw new Error('Could not load upkeep')
  return data
}
