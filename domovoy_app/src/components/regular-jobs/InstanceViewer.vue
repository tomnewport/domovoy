<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { client, getHeaders } from '@/services/domovoy'
import type { components } from '@/services/domovoy/schema.d.ts'
import { useHomesStore } from '@/stores/homes'
import { format, isThisYear } from 'date-fns'
type RegularJobInstanceSchema = components['schemas']['RegularJobInstanceSchema']
const { jobId } = defineProps<{ jobId: number }>()
const instances = ref<undefined | RegularJobInstanceSchema[]>(undefined)

async function reload() {
  const result = await client.GET('/api/regular_jobs/v1/definitions/{definition_id}/instances', {
    headers: getHeaders(),
    params: { path: { definition_id: jobId } }
  })
  instances.value = result.data?.sort((a, b) =>
    (a.completed_at || 0) < (b.completed_at || 0) ? 1 : -1
  )
}

const homesStore = useHomesStore()

watch(() => jobId, reload)

onMounted(async () => {
  await homesStore.ensureLoaded()
  await reload()
})

const headers = [
  { key: 'completed_at', title: 'Completed' },
  { key: 'completed_by', title: 'By' }
]

const DAY_MS = 1000 * 60 * 60 * 24
// Jobs done on average more than once every two days get their history in
// hours: "every 12 hours" and the time of each completion.
const HOURLY_BELOW_DAYS = 2

const summary = computed(() => {
  const list = instances.value ?? []
  const byUser = list
    .map((instance) => instance.completed_by)
    .reduce(
      (accumulator, item) => {
        accumulator[item.toString()] = (accumulator[item.toString()] || 0) + 1
        return accumulator
      },
      {} as Record<string, number>
    )

  // Average gap between completions; needs at least two of them.
  const times = list.map((inst) => new Date(inst.completed_at || 0).valueOf()).filter((t) => t > 0)
  const frequencyDays =
    times.length >= 2
      ? (Math.max(...times) - Math.min(...times)) / ((times.length - 1) * DAY_MS)
      : null

  // Only completions that had a due date can be on time or late.
  const dated = list.filter((inst) => inst.due_at && inst.completed_at)
  const onTime = dated.length
    ? dated.filter(
        (inst) => new Date(inst.due_at!).valueOf() > new Date(inst.completed_at!).valueOf()
      ).length / dated.length
    : null

  return {
    frequencyDays,
    byUser: Object.entries(byUser)
      .map(([user, count]) => ({ user, count }))
      .sort((a, b) => (a.count > b.count ? -1 : 1)),
    onTime
  }
})

const hourly = computed(
  () => summary.value.frequencyDays !== null && summary.value.frequencyDays < HOURLY_BELOW_DAYS
)

const doneEvery = computed(() => {
  const days = summary.value.frequencyDays
  if (days === null) return '—'
  if (hourly.value) {
    const hours = Math.max(1, Math.round(days * 24))
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}`
  }
  const whole = Math.round(days)
  return `${whole} ${whole === 1 ? 'day' : 'days'}`
})

function completedLabel(value: string | null | undefined) {
  if (!value) return ''
  const date = new Date(value)
  const day = isThisYear(date) ? 'EEE d MMM' : 'EEE d MMM yyyy'
  return format(date, hourly.value ? `${day}, HH:mm` : day)
}
</script>
<template>
  <v-row>
    <v-data-table
      :hide-default-footer="true"
      :hide-default-header="true"
      :headers="[
        { key: 'user', title: 'User' },
        { key: 'count', title: 'Count' }
      ]"
      :items="summary.byUser"
    >
      <template v-slot:item.user="{ item }"
        ><d-user-display variant="short">{{ item.user }}</d-user-display></template
      >
      <template v-slot:item.count="{ item }">
        <v-progress-linear
          :style="{ width: '50vw' }"
          :model-value="(item.count / (instances?.length || 0)) * 100"
          height="25"
          width="50vw"
          color="green"
        >
          <strong>{{ Math.round((item.count / (instances?.length || 0)) * 100) }}%</strong>
        </v-progress-linear>
      </template>
    </v-data-table>
  </v-row>
  <v-row class="px-8 py-6">
    <v-col cols="6">
      <v-row class="justify-center"> Done every </v-row>
      <v-row class="text-h5 justify-center">{{ doneEvery }}</v-row>
    </v-col>
    <v-col cols="6">
      <v-row class="justify-center"> On time </v-row>
      <v-row class="text-h5 justify-center">
        {{ summary.onTime === null ? '—' : `${Math.round(summary.onTime * 100)}%` }}
      </v-row>
    </v-col>
  </v-row>

  <v-data-table :headers="headers" :items="instances" :search="''">
    <template v-slot:item.completed_at="{ item }"
      >{{ completedLabel(item.completed_at) }}
      <span v-if="item.due_at">{{
        (item.completed_at || 0) < (item.due_at || 0) ? '(on time)' : '(late)'
      }}</span>
    </template>
    <template v-slot:item.completed_by="{ item }"
      ><d-user-display variant="short">{{ item.completed_by }}</d-user-display></template
    >
  </v-data-table>
</template>
