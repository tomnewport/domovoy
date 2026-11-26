<script setup lang="ts">
import { computed } from 'vue'
import PointsRaceChart from '@/components/charts/PointsRaceChart.vue'
import { memberColors } from '@/utils/memberColors'
import type { HomeStatistics } from '@/services/domovoy/stats'
import { standings, type Period } from '@/utils/progress'

// Who did what in one home this period: each member's points and share,
// ranked, and everyone's running total on the same axes.
const { stats, period, homeName } = defineProps<{
  stats: HomeStatistics
  period: Period
  homeName: string
}>()

const ranked = computed(() => standings(stats, period))
const colors = computed(() => memberColors(stats.users.map((u) => u.id)))
const leader = computed(() => Math.max(1, ranked.value[0]?.points ?? 0))
const total = computed(() => ranked.value.reduce((a, s) => a + s.points, 0))
const share = (points: number) => (total.value ? Math.round((points / total.value) * 100) : 0)
const periodLabel = computed(() => (period === 7 ? 'this week' : 'in the last 30 days'))
const name = (s: { nameShort: string; isSelf: boolean }) => (s.isSelf ? 'You' : s.nameShort)

const headline = computed(() => {
  const list = ranked.value
  if (!total.value) return `No points yet ${periodLabel.value}.`
  if (list.length < 2) return `${total.value} points ${periodLabel.value}.`
  const top = list.filter((s) => s.points === list[0].points)
  if (top.length === list.length) return `An even split ${periodLabel.value}.`
  if (top.length > 1)
    return `${top.map(name).join(' and ')} are level ${periodLabel.value}, on ${top[0].points} points each.`
  return `${name(top[0])} did the most ${periodLabel.value}: ${share(top[0].points)}% of ${total.value} points.`
})

const chartSeries = computed(() =>
  stats.users.map((user) => ({
    id: user.id,
    name: user.name_short,
    values: user.daily_scores.slice(-period),
    isSelf: user.id === stats.self
  }))
)
const chartDates = computed(() => stats.dates.slice(-period))
</script>
<template>
  <v-card class="pa-4" variant="tonal">
    <div class="text-body-medium text-medium-emphasis">Who did what {{ periodLabel }}</div>
    <div class="text-title-medium mb-3">{{ headline }}</div>

    <ol class="standings">
      <li v-for="(member, i) in ranked" :key="member.id" class="standings__row">
        <span class="standings__rank text-medium-emphasis">{{ i + 1 }}</span>
        <span class="standings__name" :class="{ 'font-weight-bold': member.isSelf }">
          {{ member.nameShort }}<template v-if="member.isSelf"> (you)</template>
        </span>
        <span class="standings__bar" aria-hidden="true">
          <span
            v-if="member.points > 0"
            class="standings__fill"
            :style="{
              width: `${(member.points / leader) * 100}%`,
              background: colors.get(member.id)
            }"
          ></span>
        </span>
        <span class="standings__points">{{ member.points }}</span>
        <span class="standings__share text-medium-emphasis">{{ share(member.points) }}%</span>
      </li>
    </ol>
    <div class="text-body-small text-medium-emphasis mt-2">
      These points include overdue bonuses; upkeep leaves them out.
    </div>

    <div class="text-body-medium text-medium-emphasis mt-4 mb-2">Running total {{ periodLabel }}</div>
    <PointsRaceChart
      :dates="chartDates"
      :series="chartSeries"
      :colors="colors"
      cumulative
      :title="`Points ${periodLabel} in ${homeName}`"
    />
  </v-card>
</template>
<style scoped>
.standings {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}
.standings__row {
  display: grid;
  grid-template-columns: 1.25rem 6.5rem 1fr 2.5rem 2.75rem;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
}
.standings__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.standings__bar {
  height: 8px;
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  overflow: hidden;
}
.standings__fill {
  display: block;
  height: 100%;
  border-radius: 0 4px 4px 0;
}
.standings__points,
.standings__share {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
