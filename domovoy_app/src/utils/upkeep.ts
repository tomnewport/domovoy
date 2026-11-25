import type { HomeUpkeep } from '@/services/domovoy/stats'
import type { RegularJobDefinition } from '@/stores/regular-job'

export interface UpkeepStatus {
  label: string
  icon: string
  color: 'success' | 'warning' | 'error'
}

// How a period's upkeep (points done ÷ ideal) reads at a glance. Always shown
// with its icon and label, never colour alone.
export function upkeepStatus(ratio: number | null): UpkeepStatus | null {
  if (ratio === null) return null
  if (ratio >= 1) return { label: 'Ahead', icon: 'mdi-check-circle', color: 'success' }
  if (ratio >= 0.9) return { label: 'Keeping up', icon: 'mdi-check-circle', color: 'success' }
  if (ratio >= 0.7) return { label: 'Slipping', icon: 'mdi-alert', color: 'warning' }
  return { label: 'Falling behind', icon: 'mdi-alert-octagon', color: 'error' }
}

const sum = (values: number[]) => values.reduce((a, b) => a + b, 0)

// Upkeep over the last `days` days (today included).
export function upkeepFor(upkeep: HomeUpkeep, days: number) {
  const points = sum(upkeep.daily_points.slice(-days))
  const ideal = (upkeep.ideal_per_week * days) / 7
  return { points, ideal, ratio: ideal > 0 ? points / ideal : null }
}

export interface PeriodCounts {
  jobs: number
  onTime: number
  dated: number // jobs that had a due date (on time or late)
}

// Jobs done in the last `days` days and in the `days` before those; the
// earlier one is null when the upkeep doesn't reach back that far.
export function countsFor(
  upkeep: HomeUpkeep,
  days: number
): { current: PeriodCounts; previous: PeriodCounts | null } {
  const n = upkeep.daily_jobs.length
  const window = (from: number, to: number): PeriodCounts => {
    const onTime = sum(upkeep.daily_on_time.slice(from, to))
    return {
      jobs: sum(upkeep.daily_jobs.slice(from, to)),
      onTime,
      dated: onTime + sum(upkeep.daily_late.slice(from, to))
    }
  }
  return {
    current: window(Math.max(0, n - days), n),
    previous: n >= days * 2 ? window(n - days * 2, n - days) : null
  }
}

// A home's jobs whose current due date has passed, most overdue first.
export function overdueJobs(
  definitions: RegularJobDefinition[],
  homeId: number,
  now = new Date()
): RegularJobDefinition[] {
  const due = (d: RegularJobDefinition) => new Date(d.next_assigned_due_date ?? 0).valueOf()
  return definitions
    .filter((d) => d.home === homeId && d.next_assigned_due_date && due(d) < now.valueOf())
    .sort((a, b) => due(a) - due(b))
}
