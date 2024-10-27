<script setup lang="ts">
import type { components } from '@/services/domovoy/schema.d.ts'
const props = defineProps<{
  jobs: components['schemas']['RegularJobDefinitionSchema'][]
  onChange: () => Promise<void>
}>()
</script>
<template>
  <v-list lines="one" class="pa-0">
    <v-list-item
      :to="`/homes/${job.home}/jobs/${job.id}`"
      v-for="job of props.jobs"
      :key="job.id || -1"
    >
      <v-list-item-title class="d-flex">
        <span>{{ job.name }}</span
        ><v-spacer
      /></v-list-item-title>
    </v-list-item>
  </v-list>
</template>
