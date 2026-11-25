<script setup lang="ts">
import { useHomesStore } from '@/stores/homes'
const homesStore = useHomesStore()
</script>
<template>
  <v-container fluid class="d-flex flex-wrap ga-3">
    <template v-if="!homesStore.homes">
      <v-card v-for="n in 2" :key="n" class="flex-grow-1" style="width: 100%" aria-hidden="true">
        <v-skeleton-loader type="heading, text, actions" color="transparent" />
      </v-card>
    </template>
    <div
      v-else-if="homesStore.homes.length === 0"
      class="d-flex flex-column align-center text-center pa-8 text-medium-emphasis"
      style="width: 100%"
    >
      <v-icon size="48" class="mb-3">mdi-home-plus-outline</v-icon>
      <div class="text-subtitle-1">You're not in a home yet</div>
      <div class="text-body-2">Create one with the + button above.</div>
    </div>
    <template v-else>
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
    </template>
  </v-container>
</template>
