<script setup lang="ts">
import type { components } from '@/services/domovoy/schema.d.ts'
import { useHomesStore } from '@/stores/homes'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { client, getHeaders } from '@/services/domovoy'
import CreateRegularJob from '@/components/regular-jobs/CreateRegularJob.vue'
import RegularJobDefinitionList from '@/components/regular-jobs/RegularJobDefinitionList.vue'
import JobEditor from '@/components/regular-jobs/JobEditor.vue'

const homesStore = useHomesStore()
const route = useRoute()
const home = computed(() =>
  homesStore.homes?.find((home) => home.id?.toString() === route.params.homeId)
)
const definitions = ref<components['schemas']['RegularJobDefinitionSchema'][]>([])
const matchedDefinitions = ref<components['schemas']['RegularJobDefinitionSchema'][]>([])
const searchTerm = ref<string>('')
const loadingJobs = ref<boolean>(true)

const SORT_LOW_HIGH = 'Lowest value'
const SORT_HIGH_LOW = 'Highest value'
const SORT_NAME_AZ = 'Name (A-Z)'
const SORT_NAME_ZA = 'Name (Z-A)'

const sortOptions = [SORT_LOW_HIGH, SORT_HIGH_LOW, SORT_NAME_AZ, SORT_NAME_ZA]

const sortType = ref<(typeof sortOptions)[number]>(SORT_NAME_AZ)

async function reload() {
  homesStore.ensureLoaded()
  const defResult = await client.GET('/api/regular_jobs/v1/definitions', {
    headers: getHeaders(),
    params: {
      query: {
        home_id: parseInt(
          typeof route.params.homeId === 'string' ? route.params.homeId : route.params.homeId[0]
        )
      }
    }
  })
  if (defResult.data) definitions.value = defResult.data
  loadingJobs.value = false
  applySortSearch()
}

function applySortSearch() {
  const sortFn = (
    a: components['schemas']['RegularJobDefinitionSchema'],
    b: components['schemas']['RegularJobDefinitionSchema']
  ) => {
    if (sortType.value === SORT_LOW_HIGH && a.value_default != b.value_default)
      return a.value_default > b.value_default ? 1 : -1
    if (sortType.value === SORT_HIGH_LOW && a.value_default != b.value_default)
      return a.value_default > b.value_default ? -1 : 1
    if (sortType.value === SORT_NAME_ZA) return a.name > b.name ? -1 : 1
    return a.name > b.name ? 1 : -1
  }
  matchedDefinitions.value = definitions.value
    .filter((def) => def.name.toLowerCase().includes(searchTerm.value.toLowerCase()))
    .sort(sortFn)
}

watch(route, async () => {
  await reload()
})

onMounted(async () => {
  await reload()
})

watch([searchTerm, sortType], applySortSearch)
</script>
<template>
  <v-toolbar color="secondary" app fixed class="fixed-bar">
    <v-btn icon :to="`/homes/${route.params.homeId}`" aria-label="Back to home">
      <v-icon>mdi-arrow-left</v-icon>
    </v-btn>
    <v-toolbar-title v-if="home">{{ home.name }} - Jobs</v-toolbar-title>
    <v-toolbar-title v-else-if="homesStore.initialized">Home not found</v-toolbar-title>
    <v-toolbar-title v-else><span class="dmv-placeholder"></span></v-toolbar-title>
    <v-spacer></v-spacer>
    <CreateRegularJob v-if="home" :homeId="route.params.homeId" :onChange="reload" />
  </v-toolbar>
  <v-container v-if="home || !homesStore.initialized">
    <v-text-field label="Search" v-model="searchTerm"></v-text-field>
    <v-select label="Sort" :items="sortOptions" v-model="sortType"></v-select>
    <JobEditor v-if="home" :back-link="`/homes/${home.id}/jobs`" />
    <template v-if="loadingJobs">
      <v-skeleton-loader
        v-for="n in 5"
        :key="n"
        type="list-item"
        color="background"
        aria-hidden="true"
      />
    </template>
    <div
      v-else-if="matchedDefinitions.length === 0"
      class="text-center pa-6 text-medium-emphasis text-body-2"
    >
      {{ searchTerm ? 'No jobs match your search.' : 'No jobs yet. Add one with the + button.' }}
    </div>
    <RegularJobDefinitionList v-else :jobs="matchedDefinitions" :onChange="reload" />
  </v-container>
</template>
