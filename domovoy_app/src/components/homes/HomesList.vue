<script setup lang="ts">
import HomeSummaryCard from './HomeSummaryCard.vue'
import { useHomesStore } from '@/stores/homes'

// Each of your homes as a summary card; `refreshKey` changes to reload their numbers.
const { refreshKey = 0 } = defineProps<{ refreshKey?: number }>()
const homesStore = useHomesStore()
</script>
<template>
  <v-container class="homes-list d-flex flex-column ga-3 pb-16">
    <template v-if="!homesStore.homes">
      <v-card v-for="n in 2" :key="n" variant="tonal" aria-hidden="true">
        <v-skeleton-loader type="heading, text, text" color="transparent" />
      </v-card>
    </template>
    <div
      v-else-if="homesStore.homes.length === 0"
      class="d-flex flex-column align-center text-center pa-8 text-medium-emphasis"
    >
      <v-icon size="48" class="mb-3">mdi-home-plus-outline</v-icon>
      <div class="text-subtitle-1">You're not in a home yet</div>
      <div class="text-body-2">Create one with the + button above.</div>
    </div>
    <template v-else>
      <HomeSummaryCard
        v-for="home of homesStore.homes"
        :key="home.id ?? home.name"
        :home="home"
        :refresh-key="refreshKey"
      />
    </template>
  </v-container>
</template>
<style scoped>
.homes-list {
  max-width: 760px;
}
</style>
