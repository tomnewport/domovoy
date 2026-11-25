<script setup lang="ts">
import { onMounted, ref } from 'vue'
import HomesList from '@/components/homes/HomesList.vue'
import CreateHome from '@/components/homes/CreateHome.vue'
import AuthWall from '@/components/auth/AuthWall.vue'
import { useHomesStore } from '@/stores/homes'
import { useRegularJobStore } from '@/stores/regular-job'

const homesStore = useHomesStore()
const regularJobStore = useRegularJobStore()
const refreshKey = ref(0)

function refresh() {
  refreshKey.value += 1
  homesStore.reloadHomes()
  regularJobStore.reload()
}

onMounted(() => {
  homesStore.reloadHomes()
  // Each card counts the home's overdue jobs from the job list.
  if (!regularJobStore.fresh) regularJobStore.reload()
})
</script>
<template>
  <AuthWall>
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-toolbar-title>Homes</v-toolbar-title>
      <v-btn icon :loading="homesStore.loading" @click="refresh" aria-label="Refresh">
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <CreateHome />
    </v-toolbar>
    <HomesList :refresh-key="refreshKey" />
  </AuthWall>
</template>
