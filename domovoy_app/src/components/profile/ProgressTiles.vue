<script setup lang="ts">
import { computed } from 'vue'
import type { Period, PeriodTotals } from './progress'

// Headline numbers for the signed-in member, each compared with the period
// before. Up is good for all of them.
const { period, points, totals, streak } = defineProps<{
  period: Period
  points: { current: number; previous: number }
  totals: { current: PeriodTotals; previous: PeriodTotals }
  streak: number
}>()

const previousLabel = computed(() => (period === 7 ? 'last week' : 'previous 30 days'))

function delta(current: number, previous: number) {
  const diff = current - previous
  if (diff === 0) return { text: `same as ${previousLabel.value}`, tone: 'flat' }
  return {
    text: `${diff > 0 ? '+' : '−'}${Math.abs(diff)} vs ${previousLabel.value}`,
    tone: diff > 0 ? 'up' : 'down'
  }
}

const onTimeRate = (t: PeriodTotals) => (t.dated ? Math.round((t.onTime / t.dated) * 100) : null)

const tiles = computed(() => {
  const now = onTimeRate(totals.current)
  const before = onTimeRate(totals.previous)
  return [
    {
      label: 'Points',
      icon: 'mdi-medal-outline',
      value: String(points.current),
      delta: delta(points.current, points.previous)
    },
    {
      label: 'Jobs done',
      icon: 'mdi-check-circle-outline',
      value: String(totals.current.jobs),
      delta: delta(totals.current.jobs, totals.previous.jobs)
    },
    {
      label: 'On time',
      icon: 'mdi-clock-check-outline',
      value: now === null ? '—' : `${now}%`,
      delta:
        now === null || before === null
          ? {
              text: now === null ? 'no deadlines yet' : `no deadlines ${previousLabel.value}`,
              tone: 'flat'
            }
          : {
              text:
                now === before
                  ? `same as ${previousLabel.value}`
                  : `was ${before}% ${previousLabel.value}`,
              tone: now > before ? 'up' : now < before ? 'down' : 'flat'
            }
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
  <div class="tiles">
    <v-card v-for="tile in tiles" :key="tile.label" class="tile pa-3" variant="tonal">
      <div class="d-flex align-center ga-1 text-body-2 text-medium-emphasis">
        <v-icon :icon="tile.icon" size="16" />
        <span>{{ tile.label }}</span>
      </div>
      <div class="text-h5 font-weight-bold mt-1">{{ tile.value }}</div>
      <div class="tile__delta text-caption" :class="`tile__delta--${tile.delta.tone}`">
        <v-icon
          v-if="tile.delta.tone !== 'flat'"
          :icon="tile.delta.tone === 'up' ? 'mdi-arrow-up' : 'mdi-arrow-down'"
          size="12"
        />
        {{ tile.delta.text }}
      </div>
    </v-card>
  </div>
</template>
<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
@media (min-width: 720px) {
  .tiles {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.tile__delta {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.tile__delta--up {
  color: rgb(var(--v-theme-success));
}
.tile__delta--down {
  color: rgb(var(--v-theme-warning));
}
</style>
