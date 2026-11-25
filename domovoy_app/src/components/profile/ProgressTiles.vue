<script setup lang="ts">
import { computed } from 'vue'
import StatTiles from '@/components/common/StatTiles.vue'
import type { Period, PeriodTotals } from '@/utils/progress'
import { compare, compareOnTime, onTimePercent, type StatTile } from '@/utils/tiles'

// Headline numbers for the signed-in member, each compared with the period
// before. Up is good for all of them.
const { period, points, totals, streak } = defineProps<{
  period: Period
  points: { current: number; previous: number }
  totals: { current: PeriodTotals; previous: PeriodTotals }
  streak: number
}>()

const previousLabel = computed(() => (period === 7 ? 'last week' : 'previous 30 days'))

const tiles = computed((): StatTile[] => {
  const now = onTimePercent(totals.current.onTime, totals.current.dated)
  const before = onTimePercent(totals.previous.onTime, totals.previous.dated)
  return [
    {
      label: 'Points',
      icon: 'mdi-medal-outline',
      value: String(points.current),
      delta: compare(points.current, points.previous, previousLabel.value)
    },
    {
      label: 'Jobs done',
      icon: 'mdi-check-circle-outline',
      value: String(totals.current.jobs),
      delta: compare(totals.current.jobs, totals.previous.jobs, previousLabel.value)
    },
    {
      label: 'On time',
      icon: 'mdi-clock-check-outline',
      value: now === null ? '—' : `${now}%`,
      delta: compareOnTime(now, before, previousLabel.value)
    },
    {
      label: 'Streak',
      icon: 'mdi-fire',
      value: `${streak} ${streak === 1 ? 'day' : 'days'}`,
      delta: {
        text: streak ? 'in a row with a job done' : 'do a job today to start one',
        tone: 'flat'
      }
    }
  ]
})
</script>
<template>
  <StatTiles :tiles="tiles" />
</template>
