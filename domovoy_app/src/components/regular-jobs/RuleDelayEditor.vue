<script setup lang="ts">
import { reactive } from 'vue'
import { type RuleDelay } from '@/stores/regular-job'
const { value, onChange } = defineProps<{
  value: RuleDelay
  onChange: (chg: RuleDelay | undefined) => Promise<void>
}>()
const values = reactive({
  days: (value.days || 0).toString(),
  weeks: (value.weeks || 0).toString(),
  months: (value.months || 0).toString()
})
// Saved when a field is left (or Enter, or the arrows), not on every
// keystroke: typing "12" would otherwise save 1 and then 12.
function save() {
  const next: RuleDelay = {
    rule: value.rule,
    days: parseInt(values.days) || 0,
    weeks: parseInt(values.weeks) || 0,
    months: parseInt(values.months) || 0
  }
  const unchanged =
    next.days === (value.days || 0) &&
    next.weeks === (value.weeks || 0) &&
    next.months === (value.months || 0)
  if (!unchanged) onChange(next)
}
</script>
<template>
  <v-card color="cyan-lighten-4" class="my-0 py-0">
    <v-card-title>Wait a fixed amount of time</v-card-title>
    <v-card-text>
      <v-row>
        <v-col>
          <v-text-field
            variant="underlined"
            label="Days"
            min="0"
            v-model="values.days"
            type="number"
            @change="save"
          ></v-text-field>
        </v-col>
        <v-col>
          <v-text-field
            variant="underlined"
            label="Weeks"
            min="0"
            v-model="values.weeks"
            type="number"
            @change="save"
          ></v-text-field>
        </v-col>
        <v-col>
          <v-text-field
            variant="underlined"
            label="Months"
            min="0"
            v-model="values.months"
            type="number"
            @change="save"
          ></v-text-field>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions
      ><v-spacer></v-spacer
      ><v-btn v-on:click="onChange(undefined)" color="error">Delete</v-btn></v-card-actions
    >
  </v-card>
</template>
