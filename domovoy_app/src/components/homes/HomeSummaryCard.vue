<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { components } from '@/services/domovoy/schema.d.ts'
import { useRegularJobStore } from '@/stores/regular-job'
import {
  fetchStatistics,
  fetchUpkeep,
  type HomeStatistics,
  type HomeUpkeep
} from '@/services/domovoy/stats'
import UpkeepMeter from './UpkeepMeter.vue'
import { memberColors } from '@/utils/memberColors'
import { standings } from '@/utils/progress'
import { overdueJobs, upkeepFor, upkeepStatus } from '@/utils/upkeep'

type Home = components['schemas']['HomeSchema']

// One home at a glance, for the Homes list: this week's upkeep, what's
// overdue, and who's done what. The whole card opens the home.
const { home, refreshKey = 0 } = defineProps<{ home: Home; refreshKey?: number }>()
const regularJobStore = useRegularJobStore()

const upkeep = ref<HomeUpkeep | null>(null)
const stats = ref<HomeStatistics | null>(null)
const failed = ref(false)

async function load() {
  failed.value = false
  try {
    const id = home.id as number
    const [u, s] = await Promise.all([fetchUpkeep(id, 7), fetchStatistics(id, 7)])
    upkeep.value = u
    stats.value = s
  } catch {
    failed.value = true
  }
}
onMounted(load)
// On refresh, keep showing the old numbers until the new ones arrive.
watch(() => refreshKey, load)

const week = computed(() => (upkeep.value ? upkeepFor(upkeep.value, 7) : null))
const status = computed(() => (week.value ? upkeepStatus(week.value.ratio) : null))
const overdue = computed(() => overdueJobs(regularJobStore.definitions, home.id as number))
const colors = computed(() => memberColors(home.memberships.map((m) => m.user.id)))
const ranked = computed(() => (stats.value ? standings(stats.value, 7) : []))
</script>
<template>
  <v-card :to="`/homes/${home.id}`" class="pa-4" variant="tonal">
    <div class="d-flex align-start">
      <div class="flex-grow-1 min-w-0">
        <div class="text-h6">{{ home.name }}</div>
        <div v-if="home.description" class="text-body-2 text-medium-emphasis text-truncate">
          {{ home.description }}
        </div>
      </div>
      <v-icon icon="mdi-chevron-right" class="text-medium-emphasis" aria-hidden="true" />
    </div>

    <div v-if="failed" class="text-body-2 text-medium-emphasis mt-3">
      <v-icon icon="mdi-alert" size="16" /> Couldn't load this week's numbers.
    </div>

    <template v-else-if="!week">
      <v-skeleton-loader type="text, text" color="transparent" class="mt-2" aria-hidden="true" />
    </template>

    <template v-else>
      <div class="d-flex align-center justify-space-between mt-3 mb-1">
        <span class="text-body-2 text-medium-emphasis">Upkeep this week</span>
        <v-chip
          v-if="status"
          :color="status.color"
          :prepend-icon="status.icon"
          size="small"
          variant="tonal"
        >
          {{ status.label }}
        </v-chip>
      </div>
      <template v-if="week.ratio !== null">
        <div class="d-flex align-baseline ga-2">
          <span class="text-h5 font-weight-bold">{{ Math.round(week.ratio * 100) }}%</span>
          <span class="text-body-2 text-medium-emphasis">
            {{ week.points }} of {{ Math.round(week.ideal) }} points
          </span>
        </div>
        <UpkeepMeter
          :ratio="week.ratio"
          :status="status"
          :label="`${home.name} upkeep this week`"
          class="mt-1"
        />
      </template>
      <div v-else class="text-body-2 text-medium-emphasis">No scheduled jobs yet.</div>

      <div class="d-flex flex-wrap align-center ga-3 mt-3 text-body-2">
        <span v-if="regularJobStore.hasData" class="d-inline-flex align-center ga-1">
          <template v-if="overdue.length">
            <v-icon icon="mdi-alert" color="warning" size="16" />
            {{ overdue.length }} overdue
          </template>
          <template v-else>
            <v-icon icon="mdi-check-circle-outline" color="success" size="16" />
            Nothing overdue
          </template>
        </span>
        <span
          v-for="member in ranked"
          :key="member.id"
          class="d-inline-flex align-center ga-1"
          :class="{ 'font-weight-bold': member.isSelf }"
        >
          <span
            class="member-dot"
            :style="{ background: colors.get(member.id) }"
            aria-hidden="true"
          ></span>
          {{ member.isSelf ? 'You' : member.nameShort }} {{ member.points }}
        </span>
      </div>
    </template>
  </v-card>
</template>
<style scoped>
.min-w-0 {
  min-width: 0;
}
.member-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
