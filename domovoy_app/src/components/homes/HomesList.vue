<script setup lang="ts">
import { useHomesStore } from '@/stores/homes'
const homesStore = useHomesStore()
</script>
<template>
  <v-container fluid class="d-flex flex-wrap ga-3">
    <v-card
      class="flex-grow-1"
      style="width: 100%"
      v-for="home of homesStore.homes"
      :key="home.name"
      :title="home.name"
      :subtitle="home.description || ''"
    >
      <v-card-actions>
        <v-spacer></v-spacer><v-btn :to="`/homes/${home.id}`">Edit</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
