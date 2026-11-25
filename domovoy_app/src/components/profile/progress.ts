import { differenceInCalendarDays, startOfDay, subDays } from 'date-fns'
import type { HomeStatistics, JobCompletion } from '@/services/domovoy/stats'

export type Period = 7 | 30

export interface PeriodTotals {
  points: number
  jobs: number
  onTime: number // completions that had a due date and met it
  dated: number // completions that had a due date at all
}

// Statistics are fetched for twice the period, so the second half is "this
// period" and the first half the one before it, for comparison.
export function pointsByPeriod(stats: HomeStatistics[], userId: number, period: Period) {
  let current = 0
  let previous = 0
  for (const home of stats) {
    const scores = home.users.find((u) => u.id === userId)?.daily_scores ?? []
    const split = scores.length - period
    scores.forEach((value, i) => {
      if (i >= split) current += value
      else previous += value
    })
  }
  return { current, previous }
}

export function completionsByPeriod(
  completions: JobCompletion[],
  period: Period,
  now = new Date()
): { current: PeriodTotals; previous: PeriodTotals } {
  const currentStart = subDays(startOfDay(now), period - 1)
  const previousStart = subDays(currentStart, period)
  const empty = (): PeriodTotals => ({ points: 0, jobs: 0, onTime: 0, dated: 0 })
  const totals = { current: empty(), previous: empty() }
  for (const completion of completions) {
    const at = new Date(completion.completed_at)
    const bucket =
      at >= currentStart ? totals.current : at >= previousStart ? totals.previous : null
    if (!bucket) continue
    bucket.points += completion.value
    bucket.jobs += 1
    if (completion.on_time !== null && completion.on_time !== undefined) {
      bucket.dated += 1
      if (completion.on_time) bucket.onTime += 1
    }
  }
  return totals
}

// Days in a row, up to today, with at least one job done. A day with nothing
// yet today doesn't break the streak until it's over.
export function currentStreak(completions: JobCompletion[], now = new Date()): number {
  const daysAgo = new Set(
    completions.map((c) => differenceInCalendarDays(now, new Date(c.completed_at)))
  )
  let day = daysAgo.has(0) ? 0 : 1
  let streak = 0
  while (daysAgo.has(day)) {
    streak += 1
    day += 1
  }
  return streak
}

export interface Standing {
  id: number
  name: string
  nameShort: string
  points: number
  isSelf: boolean
}

// Members of one home ranked by points earned this period.
export function standings(stats: HomeStatistics, period: Period): Standing[] {
  return stats.users
    .map((user) => ({
      id: user.id,
      name: user.name,
      nameShort: user.name_short,
      points: user.daily_scores.slice(-period).reduce((a, b) => a + b, 0),
      isSelf: user.id === stats.self
    }))
    .sort((a, b) => b.points - a.points || a.nameShort.localeCompare(b.nameShort))
}

export function ordinal(n: number): string {
  const tens = n % 100
  if (tens >= 11 && tens <= 13) return `${n}th`
  return `${n}${['th', 'st', 'nd', 'rd'][n % 10] ?? 'th'}`
}
