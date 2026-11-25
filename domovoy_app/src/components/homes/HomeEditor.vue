<script setup lang="ts">
import { useHomesStore } from '@/stores/homes'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import EditableItem from '@/components/common/EditableItem.vue'
import { client, getHeaders } from '@/services/domovoy'

const homesStore = useHomesStore()
const route = useRoute()
// Reactive, so a cached home shows at once and updates when the list refreshes.
const home = computed(() =>
  homesStore.homes?.find((home) => home.id?.toString() === route.params.homeId)
)

onMounted(() => {
  homesStore.ensureLoaded()
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
}
</script>
<template>
  <template v-if="home">
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-btn icon to="/homes" aria-label="Back to homes">
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
  <template v-else>
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-btn icon to="/homes" aria-label="Back to homes">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <v-toolbar-title v-if="homesStore.initialized">Home not found</v-toolbar-title>
      <v-toolbar-title v-else><span class="dmv-placeholder"></span></v-toolbar-title>
    </v-toolbar>
    <v-container v-if="!homesStore.initialized" aria-hidden="true">
      <v-skeleton-loader type="text, text, button" color="transparent" />
    </v-container>
  </template>
</template>
