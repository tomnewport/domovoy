<script setup lang="ts">
import type { RuleComputeResult } from '@/stores/regular-job'

const { value } = defineProps<{ value: RuleComputeResult }>()

const total = (rolls: number[]) => rolls.reduce((a, b) => a + b, 0)
</script>
<template>
  <v-list class="py-0">
    <v-list-item
      class="px-0 py-2"
      :key="participant.user_id"
      v-for="participant in value.participants"
    >
      <v-list-item-title>
        <v-icon v-if="participant.user_id === value.assignee">mdi-hand-pointing-right</v-icon>
        {{ participant.user_name }}
      </v-list-item-title>
      <v-list-item-subtitle>
        <!-- A roll of 0 marks the current assignee, kept when the job was edited. -->
        <v-icon
          :key="idx"
          v-for="(roll, idx) of participant.rolls"
          :title="roll === 0 ? 'Kept as assignee' : undefined"
          >{{ roll === 0 ? 'mdi-pin' : `mdi-dice-${roll}` }}</v-icon
        >
        =
        {{ total(participant.rolls) }}
      </v-list-item-subtitle>
    </v-list-item>
  </v-list>
</template>
