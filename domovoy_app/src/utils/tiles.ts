// Headline numbers shown as a grid of tiles (Profile, a home's overview).

export type Tone = 'up' | 'down' | 'flat'

export interface StatTile {
  label: string
  icon: string
  value: string
  delta: { text: string; tone: Tone }
}

// "+3 vs last week", where more is better. Pass `lowerIsBetter` for counts
// such as overdue jobs.
export function compare(
  current: number,
  previous: number,
  previousLabel: string,
  { lowerIsBetter = false } = {}
): StatTile['delta'] {
  const diff = current - previous
  if (diff === 0) return { text: `same as ${previousLabel}`, tone: 'flat' }
  const better = lowerIsBetter ? diff < 0 : diff > 0
  return {
    text: `${diff > 0 ? '+' : '−'}${Math.abs(diff)} vs ${previousLabel}`,
    tone: better ? 'up' : 'down'
  }
}

// On-time rate as a whole percentage, or null with nothing that had a due date.
export const onTimePercent = (onTime: number, dated: number) =>
  dated ? Math.round((onTime / dated) * 100) : null

export function compareOnTime(
  now: number | null,
  before: number | null,
  previousLabel: string
): StatTile['delta'] {
  if (now === null) return { text: 'no deadlines yet', tone: 'flat' }
  if (before === null) return { text: `no deadlines ${previousLabel}`, tone: 'flat' }
  if (now === before) return { text: `same as ${previousLabel}`, tone: 'flat' }
  return { text: `was ${before}% ${previousLabel}`, tone: now > before ? 'up' : 'down' }
}
