<script setup lang="ts">
import type { components } from '@/services/domovoy/schema'
import { useHomesStore } from '@/stores/homes'
import { onMounted } from 'vue'
import { ref } from 'vue'
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import EditableItem from '@/components/common/EditableItem.vue'
import { client, getHeaders } from '@/services/domovoy'

const homesStore = useHomesStore()
const route = useRoute()
const home = ref<undefined | components['schemas']['HomeSchema']>(undefined)

async function findHome() {
  await homesStore.ensureLoaded()
  home.value = homesStore.homes?.find((home) => home.id?.toString() === route.params.homeId)
}

watch(route, () => {
  findHome()
})

onMounted(() => {
  findHome()
})

async function setName(name: string) {
  const homeId = home.value?.id
  if (!homeId) throw new Error('No home selected')
  await client.PATCH('/api/homes/v1/homes/{home_id}', {
    params: { path: { home_id: homeId.toString() } },
    body: { name },
    headers: getHeaders()
  })
  await homesStore.reloadHomes()
  findHome()
}

async function setDescription(description: string) {
  const homeId = home.value?.id
  if (!homeId) throw new Error('No home selected')
  await client.PATCH('/api/homes/v1/homes/{home_id}', {
    params: { path: { home_id: homeId.toString() } },
    body: { description },
    headers: getHeaders()
  })
  await homesStore.reloadHomes()
  findHome()
}
</script>
<template>
  <template v-if="home">
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-btn icon to="/homes">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <v-toolbar-title>{{ home.name }}</v-toolbar-title>
    </v-toolbar>
    <v-container>
      <EditableItem label="Name" :value="home.name" :onChange="setName" />
      <EditableItem
        label="Description"
        :value="home.description || ''"
        :onChange="setDescription"
      />
      <v-btn :to="`/homes/${route.params.homeId}/jobs`">Edit Jobs</v-btn>
    </v-container>
  </template>
</template>
