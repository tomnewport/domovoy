<script setup lang="ts">
import type { components } from '@/services/domovoy/schema'
import { useHomesStore } from '@/stores/homes'
import { onMounted } from 'vue'
import { ref } from 'vue'
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { client, getHeaders } from '@/services/domovoy'
import CreateRegularJob from '@/components/regular-jobs/CreateRegularJob.vue'
import RegularJobDefinitionList from '@/components/regular-jobs/RegularJobDefinitionList.vue'
import JobEditor from '@/components/regular-jobs/JobEditor.vue'

const homesStore = useHomesStore()
const route = useRoute()
const home = ref<undefined | components['schemas']['HomeSchema']>(undefined)
const definitions = ref<components['schemas']['RegularJobDefinitionSchema'][]>([])
const matchedDefinitions = ref<components['schemas']['RegularJobDefinitionSchema'][]>([])
const searchTerm = ref<string>('')

const SORT_LOW_HIGH = 'Lowest value'
const SORT_HIGH_LOW = 'Highest value'
const SORT_NAME_AZ = 'Name (A-Z)'
const SORT_NAME_ZA = 'Name (Z-A)'

const sortOptions = [SORT_LOW_HIGH, SORT_HIGH_LOW, SORT_NAME_AZ, SORT_NAME_ZA]

const sortType = ref<(typeof sortOptions)[number]>(SORT_NAME_AZ)

async function reload() {
  await homesStore.ensureLoaded()
  home.value = homesStore.homes?.find((home) => home.id?.toString() === route.params.homeId)
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
  <template v-if="home">
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-btn icon :to="`/homes/${route.params.homeId}`">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <v-toolbar-title>{{ home.name }} - Jobs</v-toolbar-title>
      <v-spacer></v-spacer>
      <CreateRegularJob :homeId="route.params.homeId" :onChange="reload" />
    </v-toolbar>
    <v-container>
      <v-text-field label="Search" v-model="searchTerm"></v-text-field>
      <v-select label="Sort" :items="sortOptions" v-model="sortType"></v-select>
      <JobEditor />
      <RegularJobDefinitionList :jobs="matchedDefinitions" :onChange="reload" />
    </v-container>
  </template>
</template>
