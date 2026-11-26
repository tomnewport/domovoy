<script setup lang="ts">
import { computed, ref } from 'vue'
import { startOfDay, subDays } from 'date-fns'
import type { JobCompletion } from '@/services/domovoy/stats'
import type { Period } from '@/utils/progress'

// The jobs you did this period, most points first. `homeLabel` names a
// job's home, or is empty when you have only one.
const { completions, period, homeLabel } = defineProps<{
  completions: JobCompletion[]
  period: Period
  homeLabel: (homeId: number) => string
}>()

const SHOWN = 5
const expanded = ref(false)
const periodLabel = computed(() => (period === 7 ? 'this week' : 'in the last 30 days'))

const jobs = computed(() => {
  const start = subDays(startOfDay(new Date()), period - 1)
  const byJob = new Map<
    number,
    { id: number; name: string; home: string; count: number; points: number }
  >()
  for (const c of completions) {
    if (new Date(c.completed_at) < start) continue
    const entry = byJob.get(c.job_id) ?? {
      id: c.job_id,
      name: c.job_name,
      home: homeLabel(c.home_id),
      count: 0,
      points: 0
    }
    entry.count += 1
    entry.points += c.value
    byJob.set(c.job_id, entry)
  }
  return [...byJob.values()].sort((a, b) => b.points - a.points || a.name.localeCompare(b.name))
})
const shown = computed(() => (expanded.value ? jobs.value : jobs.value.slice(0, SHOWN)))
</script>
<template>
  <v-card class="pa-4" variant="tonal">
    <div class="text-body-medium text-medium-emphasis mb-1">What you did {{ periodLabel }}</div>
    <div v-if="!jobs.length" class="text-body-medium text-medium-emphasis py-2">
      Nothing yet. Your jobs will show up here.
    </div>
    <v-table v-else density="compact" class="bg-transparent">
      <thead>
        <tr>
          <th>Job</th>
          <th class="text-right">Times</th>
          <th class="text-right">Points</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in shown" :key="job.id">
          <td>
            {{ job.name }}
            <span v-if="job.home" class="text-medium-emphasis"> · {{ job.home }}</span>
          </td>
          <td class="text-right">{{ job.count }}</td>
          <td class="text-right">{{ job.points }}</td>
        </tr>
      </tbody>
    </v-table>
    <v-btn
      v-if="jobs.length > SHOWN"
      variant="text"
      size="small"
      class="mt-1 px-1"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show fewer' : `Show all ${jobs.length}` }}
    </v-btn>
  </v-card>
</template>
