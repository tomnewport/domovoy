<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRegularJobStore, type RegularJobDefinition } from '@/stores/regular-job'
import { useCurrentUser } from '@/lookups/user'
const { jobDefinition, onClose } = defineProps<{
  jobDefinition: RegularJobDefinition
  onClose: () => void
}>()
const regularJobStore = useRegularJobStore()
const value = ref<number>(jobDefinition.value_default)
async function claim() {
  if (!jobDefinition.id) throw new Error('No definition Id')
  await regularJobStore.claim({ definitionId: jobDefinition.id, value: value.value })
  onClose()
}

async function snooze(date: string) {
  await regularJobStore.snooze(jobDefinition.id || -1, date)
  onClose()
}
const available = computed(() => {
  return new Date(jobDefinition.next_assigned_start_date || 0) > new Date()
})
const me = useCurrentUser()

const mine = computed(() => me.value?.id === jobDefinition.next_assigned_to)
</script>

<template>
  <v-card>
    <v-card-title class="d-flex"
      ><span>{{ jobDefinition.name }}</span>
      <v-spacer></v-spacer>
      <v-btn size="small" variant="plain" icon :to="`/tasks/${jobDefinition.id}/edit`"
        ><v-icon>mdi-pencil</v-icon></v-btn
      ></v-card-title
    >
    <v-card-subtitle class="d-flex">
      <span
        ><d-user-display>{{ jobDefinition.next_assigned_to }}</d-user-display></span
      >
      <v-spacer></v-spacer>
      <span
        ><d-date-display>{{ jobDefinition.next_assigned_due_date }}</d-date-display></span
      >
    </v-card-subtitle>

    <v-list>
      <v-list-item>
        {{ jobDefinition.description }}
      </v-list-item>
      <v-list-item v-if="jobDefinition.value_min === jobDefinition.value_max"
        ><template v-slot:prepend> <v-icon icon="mdi-medal"></v-icon> </template
        >{{ jobDefinition.value_default }} points</v-list-item
      >
      <v-list-item v-if="!mine && jobDefinition.bonus"
        ><template v-slot:prepend> <v-icon icon="mdi-cash-clock"></v-icon> </template
        >{{ jobDefinition.bonus }} bonus</v-list-item
      >
    </v-list>
    <v-slider
      v-if="jobDefinition.value_min < jobDefinition.value_max"
      hoist
      step="1"
      thumb-label
      v-model="value"
      :min="jobDefinition.value_min"
      :max="jobDefinition.value_max"
    >
      <template v-slot:prepend>{{ jobDefinition.value_min }}</template>
      <template v-slot:append>{{ jobDefinition.value_max }}</template>
    </v-slider>
    <v-card-actions>
      <v-btn v-on:click="onClose">Cancel</v-btn>
      <v-spacer></v-spacer>
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn
            v-on:focus="regularJobStore.loadSnoozeOptions(jobDefinition.id || -1)"
            v-bind="props"
            color="secondary"
            prepend-icon="mdi-medal"
            >Snooze</v-btn
          >
        </template>
        <v-list>
          <v-list-item
            :value="option.date"
            v-for="option in regularJobStore.snoozeOptions"
            :key="option.label"
            v-on:click="snooze(option.date)"
          >
            <v-list-item-title
              ><d-date-display variant="natural">{{
                option.date
              }}</d-date-display></v-list-item-title
            >
          </v-list-item>
        </v-list>
      </v-menu>
      <v-btn v-on:click="claim" prepend-icon="mdi-clock" color="primary">Claim</v-btn>
    </v-card-actions>
  </v-card>
</template>
