<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { type RuleCalendar } from '@/stores/regular-job'
const { value, onChange } = defineProps<{
  value: RuleCalendar
  onChange: (chg: RuleCalendar | undefined) => Promise<void>
}>()

const search = ref<null | string>(null)

const values = reactive({
  query: value.query,
  match: value.match
})

watch(values, async () => {
  await onChange({
    rule: value.rule,
    query: values.query,
    match: values.match
  })
})

const suggestions = {
  '%B': [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December'
  ],
  '%A': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
  '%W': [],
  '%m-%d': []
}
</script>
<template>
  <v-card color="purple-lighten-4" class="my-0 py-0">
    <v-card-title>Find a specific day or date</v-card-title>
    <v-card-text>
      <v-select
        variant="underlined"
        label="When"
        :items="[
          { title: 'Month name', value: '%B' },
          { title: 'Week number', value: '%W' },
          { title: 'Weekday name', value: '%A' },
          { title: 'Month and day', value: '%m-%d' }
        ]"
        v-model="values.query"
      ></v-select>
      <v-combobox
        variant="underlined"
        label="Is one of"
        :hide-no-data="false"
        v-model:search="search"
        chips
        multiple
        v-model="values.match"
        :items="suggestions[values.query] || []"
      >
        <template v-slot:no-data>
          <v-list-item v-if="search">
            <v-list-item-title>
              Press <kbd>enter</kbd> to add <strong>{{ search }}</strong>
            </v-list-item-title>
          </v-list-item>
        </template>
      </v-combobox>
    </v-card-text>
    <v-card-actions
      ><v-spacer></v-spacer
      ><v-btn v-on:click="onChange(undefined)" color="error">Delete</v-btn></v-card-actions
    >
  </v-card>
</template>
