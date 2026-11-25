<script setup lang="ts">
import HomesList from '@/components/homes/HomesList.vue'
import CreateHome from '@/components/homes/CreateHome.vue'
import AuthWall from '@/components/auth/AuthWall.vue'
import { useHomesStore } from '@/stores/homes'
import { onMounted } from 'vue'

const homesStore = useHomesStore()

onMounted(() => {
  homesStore.reloadHomes()
})
</script>
<template>
  <AuthWall>
    <v-toolbar color="secondary" app fixed class="fixed-bar">
      <v-toolbar-title>Homes</v-toolbar-title>
      <v-btn
        icon
        :loading="homesStore.loading"
        v-on:click="homesStore.reloadHomes"
        aria-label="Refresh"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <CreateHome />
    </v-toolbar>
    <HomesList />
  </AuthWall>
</template>
