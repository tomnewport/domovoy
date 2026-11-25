<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { formatDistanceToNowStrict } from 'date-fns'
import HomeUpkeep from './HomeUpkeep.vue'
import HomeStandings from './HomeStandings.vue'
import StatTiles from '@/components/common/StatTiles.vue'
import { useRegularJobStore } from '@/stores/regular-job'
import {
  fetchStatistics,
  fetchUpkeep,
  type HomeStatistics,
  type HomeUpkeep as Upkeep
} from '@/services/domovoy/stats'
import type { Period } from '@/utils/progress'
import { countsFor, overdueJobs } from '@/utils/upkeep'
import { compare, compareOnTime, onTimePercent, type StatTile } from '@/utils/tiles'

// How one home is doing: upkeep against its ideal, jobs done and on time,
// what's overdue now, and who did what.
const { homeId, homeName } = defineProps<{ homeId: number; homeName: string }>()
const regularJobStore = useRegularJobStore()

const period = ref<Period>(7)
// Fetched once for the longest period, so switching period is instant:
// 60 days of upkeep covers 30 days and the 30 before, and eight weekly columns.
const upkeep = ref<Upkeep | null>(null)
const stats = ref<HomeStatistics | null>(null)
const loadError = ref<string | null>(null)

async function load() {
  loadError.value = null
  try {
    const [u, s] = await Promise.all([fetchUpkeep(homeId, 60), fetchStatistics(homeId, 30)])
    upkeep.value = u
    stats.value = s
  } catch {
    loadError.value = 'Could not load this home’s stats.'
  }
}

onMounted(load)
watch(
  () => homeId,
  () => {
    upkeep.value = null
    stats.value = null
    load()
  }
)

const previousLabel = computed(() => (period.value === 7 ? 'last week' : 'previous 30 days'))
const overdue = computed(() => overdueJobs(regularJobStore.definitions, homeId))

const tiles = computed((): StatTile[] => {
  if (!upkeep.value) return []
  const { current, previous } = countsFor(upkeep.value, period.value)
  const now = onTimePercent(current.onTime, current.dated)
  const before = previous ? onTimePercent(previous.onTime, previous.dated) : null
  const oldest = overdue.value[0]
  return [
    {
      label: 'Jobs done',
      icon: 'mdi-check-circle-outline',
      value: String(current.jobs),
      delta: previous
        ? compare(current.jobs, previous.jobs, previousLabel.value)
        : { text: 'nothing to compare yet', tone: 'flat' }
    },
    {
      label: 'On time',
      icon: 'mdi-clock-check-outline',
      value: now === null ? '—' : `${now}%`,
      delta: compareOnTime(now, before, previousLabel.value)
    },
    {
      label: 'Overdue now',
      icon: overdue.value.length ? 'mdi-alert' : 'mdi-check-circle-outline',
      value: regularJobStore.hasData ? String(overdue.value.length) : '…',
      delta: oldest
        ? {
            text: `${oldest.name}, due ${formatDistanceToNowStrict(
              new Date(oldest.next_assigned_due_date as string)
            )} ago`,
            tone: 'flat'
          }
        : { text: 'everything’s on schedule', tone: 'flat' }
    }
  ]
})
</script>
<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-3">
      <div class="text-body-2 text-medium-emphasis">How the home is doing</div>
      <v-btn-toggle v-model="period" mandatory density="compact" variant="outlined" divided>
        <v-btn :value="7">7 days</v-btn>
        <v-btn :value="30">30 days</v-btn>
      </v-btn-toggle>
    </div>

    <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">
      {{ loadError }}
      <template #append>
        <v-btn variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>

    <template v-else-if="!upkeep || !stats">
      <v-skeleton-loader type="heading, text, image" class="mb-4" aria-hidden="true" />
      <div class="skeleton-tiles mb-4" aria-hidden="true">
        <v-skeleton-loader v-for="n in 3" :key="n" type="heading, text" />
      </div>
      <v-skeleton-loader type="heading, list-item, list-item, image" aria-hidden="true" />
    </template>

    <template v-else>
      <v-card class="pa-4 mb-4" variant="tonal">
        <HomeUpkeep :upkeep="upkeep" :period="period" />
      </v-card>
      <StatTiles :tiles="tiles" class="mb-4" />
      <HomeStandings :stats="stats" :period="period" :home-name="homeName" />
    </template>
  </div>
</template>
<style scoped>
.skeleton-tiles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
</style>
