<script setup lang="ts">
import HomesList from '@/components/homes/HomesList.vue'
import CreateHome from '@/components/homes/CreateHome.vue'
import { useHomesStore } from '@/stores/homes'
import { onMounted } from 'vue'

const homesStore = useHomesStore()

onMounted(() => {
  homesStore.reloadHomes()
})
</script>
<template>
  <v-toolbar color="secondary" app fixed class="fixed-bar">
    <v-toolbar-title>Homes</v-toolbar-title>
    <v-btn icon v-on:click="homesStore.reloadHomes">
      <v-icon>mdi-refresh</v-icon>
    </v-btn>
    <CreateHome />
  </v-toolbar>
  <HomesList />
</template>
