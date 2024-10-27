<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { client, getHeaders } from '@/services/domovoy'
import type { components } from '@/services/domovoy/schema.d.ts'
import { useHomesStore } from '@/stores/homes'
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

const summary = computed(() => {
  if (!instances.value) return {}
  const byUser = instances.value
    .map((instance) => instance.completed_by)
    .reduce(
      (accumulator, item) => {
        accumulator[item.toString()] = (accumulator[item.toString()] || 0) + 1
        return accumulator
      },
      {} as Record<string, number>
    )
  const earliest = Math.min(
    ...instances.value.map((inst) => new Date(inst.completed_at || 0).valueOf() || 0)
  )
  const latest = Math.max(
    ...instances.value.map((inst) => new Date(inst.completed_at || 0).valueOf() || 0)
  )
  const frequencyDays = (latest - earliest) / ((instances.value.length - 1) * 1000 * 60 * 60 * 24)
  const byTimeliness = instances.value
    .map(
      (instance) =>
        new Date(instance.due_at || 0).valueOf() > new Date(instance.completed_at || 0).valueOf()
    )
    .reduce(
      (accumulator, item) => {
        accumulator[item.toString()] = (accumulator[item.toString()] || 0) + 1
        return accumulator
      },
      {} as Record<string, number>
    )
  return {
    frequencyDays,
    byUser: Object.entries(byUser)
      .map(([user, count]) => ({ user, count }))
      .sort((a, b) => (a.count > b.count ? -1 : 1)),
    onTime: byTimeliness['true'] / (byTimeliness['true'] + byTimeliness['false'])
  }
})
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
      <v-row class="text-h5 justify-center">
        {{ Math.floor(summary.frequencyDays || 0) }} days
      </v-row>
    </v-col>
    <v-col cols="6">
      <v-row class="justify-center"> On time </v-row>
      <v-row class="text-h5 justify-center"> {{ Math.floor((summary.onTime || 0) * 100) }}% </v-row>
    </v-col>
  </v-row>

  <v-data-table :headers="headers" :items="instances" :search="''">
    <template v-slot:item.completed_at="{ item }"
      ><d-date-display>{{ item.completed_at }}</d-date-display>
      <span v-if="item.due_at">{{
        (item.completed_at || 0) < (item.due_at || 0) ? '(on time)' : '(late)'
      }}</span>
    </template>
    <template v-slot:item.completed_by="{ item }"
      ><d-user-display variant="short">{{ item.completed_by }}</d-user-display></template
    >
  </v-data-table>
</template>
