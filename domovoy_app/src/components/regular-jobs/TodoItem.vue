<script setup lang="ts">
import type { RegularJobDefinition } from '@/stores/regular-job'
import { JobClassification } from './utils'

const {
  job,
  onClick,
  classification,
  showDate = 'due'
} = defineProps<{
  classification: JobClassification
  job: RegularJobDefinition
  onClick: () => void
  showDate?: 'due' | 'assigned'
}>()
</script>
<template>
  <v-list-item
    v-on:click="onClick"
    :style="{ opacity: classification === JobClassification.FUTURE ? 0.5 : 1 }"
  >
    <v-list-item-title class="d-flex">
      <span
        :style="{ maxWidth: 'calc(100vw - 150px)', overflow: 'hidden', textOverflow: 'ellipsis' }"
        >{{ job.name }}</span
      >
      <v-spacer></v-spacer>
      <span v-if="job.next_assigned_to" class="text-body-2"
        ><d-user-display variant="short">{{ job.next_assigned_to }}</d-user-display></span
      >
    </v-list-item-title>
    <v-list-item-subtitle class="d-flex">
      <span>
        <d-home-display>{{ job.home }}</d-home-display>
      </span>
      <v-spacer></v-spacer>
      <span v-if="classification === JobClassification.UNSCHEDULED">Not scheduled</span>
      <span v-else-if="showDate === 'due'">
        <d-date-display variant="natural">{{ job.next_assigned_due_date }}</d-date-display>
      </span>
      <span v-else-if="showDate === 'assigned'">
        assigned <d-date-display variant="natural">{{ job.next_assigned_date }}</d-date-display>
      </span>
    </v-list-item-subtitle>
    <template v-slot:prepend>
      <v-avatar v-if="classification === JobClassification.URGENT" color="red" class="pulse">
        <v-icon color="white">mdi-alert-circle</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.PRIORITY" color="blue-darken-2">
        <v-icon color="white">mdi-alert-decagram</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.OVERDUE" color="orange">
        <v-icon color="white">mdi-bell</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.ASSIGNED" color="blue">
        <v-icon color="white">mdi-calendar-check</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.IN_HOME" color="white">
        <v-icon color="blue-lighten-1">mdi-calendar-check</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.FUTURE" color="white">
        <v-icon color="blue-lighten-1">mdi-calendar</v-icon>
      </v-avatar>
      <v-avatar v-else-if="classification === JobClassification.UNSCHEDULED" color="white">
        <v-icon color="blue-lighten-1">mdi-calendar-blank-outline</v-icon>
      </v-avatar>
    </template>
  </v-list-item>
</template>
