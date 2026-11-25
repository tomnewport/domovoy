<script setup lang="ts">
import { computed } from 'vue'
import PointsRaceChart from '@/components/charts/PointsRaceChart.vue'
import HomeUpkeep from './HomeUpkeep.vue'
import { memberColors } from '@/utils/memberColors'
import type { HomeStatistics, HomeUpkeep as Upkeep } from '@/services/domovoy/stats'
import { ordinal, standings, type Period } from './progress'

// Where you stand in one home this period: a ranked list and everyone's
// running total on the same axes.
const { stats, period, homeName, upkeep } = defineProps<{
  stats: HomeStatistics
  period: Period
  homeName: string
  upkeep?: Upkeep
}>()

const ranked = computed(() => standings(stats, period))
const colors = computed(() => memberColors(stats.users.map((u) => u.id)))
const leader = computed(() => Math.max(1, ranked.value[0]?.points ?? 0))
const periodLabel = computed(() => (period === 7 ? 'this week' : 'in the last 30 days'))

const headline = computed(() => {
  const list = ranked.value
  if (list.length < 2) return `${list[0]?.points ?? 0} points ${periodLabel.value}.`
  const me = list.findIndex((s) => s.isSelf)
  if (me < 0) return ''
  const mine = list[me]
  const tiedWithLeader = mine.points === list[0].points
  if (mine.points === 0 && tiedWithLeader)
    return `No points yet ${periodLabel.value}. First job wins.`
  if (tiedWithLeader) {
    const tied = list.filter((s) => s.points === mine.points).length
    if (tied > 1) return `You're tied for 1st ${periodLabel.value}.`
    const gap = mine.points - list[1].points
    return `You're 1st ${periodLabel.value}, ${gap} ${gap === 1 ? 'point' : 'points'} ahead of ${list[1].nameShort}.`
  }
  const ahead = list[me - 1]
  const gap = ahead.points - mine.points
  return `You're ${ordinal(me + 1)} of ${list.length} ${periodLabel.value}, ${gap} ${gap === 1 ? 'point' : 'points'} behind ${ahead.nameShort}.`
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
    <div class="text-overline text-medium-emphasis">{{ homeName }}</div>
    <template v-if="upkeep">
      <HomeUpkeep :upkeep="upkeep" :period="period" />
      <v-divider class="my-4" />
    </template>
    <div class="text-subtitle-1 mb-3">{{ headline }}</div>

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
      </li>
    </ol>

    <div class="text-body-2 text-medium-emphasis mt-4 mb-2">Running total {{ periodLabel }}</div>
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
  grid-template-columns: 1.25rem 6.5rem 1fr 2.5rem;
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
.standings__points {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
