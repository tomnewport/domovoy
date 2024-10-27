<script setup lang="ts">
import { ref, watch } from 'vue'
import RuleDelayEditor from './RuleDelayEditor.vue'
import RuleCalendarEditor from './RuleCalendarEditor.vue'
import { type Ruleset, type RuleCalendar, type RuleDelay } from '@/stores/regular-job'
const { value, onChange } = defineProps<{
  value: Ruleset
  onChange: (rules: Ruleset) => Promise<void>
}>()

const createType = ref<undefined | 'calendar:v1' | 'delay:v1'>(undefined)

async function create() {
  if (createType.value === 'delay:v1') {
    const newRule: RuleDelay = {
      rule: 'delay:v1'
    }
    await onChange({ rules: [...value.rules, newRule] })
    createType.value = undefined
  }
  if (createType.value === 'calendar:v1') {
    const newRule: RuleCalendar = {
      rule: 'calendar:v1',
      query: '%B',
      match: []
    }
    await onChange({ rules: [...value.rules, newRule] })
    createType.value = undefined
  }
}

async function setRule(changeIdx: number, changeValue: undefined | RuleCalendar | RuleDelay) {
  const rules: Ruleset = {
    rules: value.rules
      .map((rule: RuleCalendar | RuleDelay, idx: number) =>
        changeIdx === idx ? changeValue : rule
      )
      .filter((v) => v !== undefined) as (RuleCalendar | RuleDelay)[]
  }
  await onChange(rules)
}
</script>
<template>
  <v-list :key="idx" v-for="(rule, idx) of value.rules" class="ma-1">
    <RuleDelayEditor
      :value="rule"
      :onChange="(value: RuleDelay | undefined) => setRule(idx, value)"
      v-if="rule.rule === 'delay:v1'"
    />
    <RuleCalendarEditor
      :value="rule"
      :onChange="(value: RuleCalendar | undefined) => setRule(idx, value)"
      v-if="rule.rule === 'calendar:v1'"
    />
  </v-list>
  <v-select
    variant="underlined"
    :items="[
      { value: 'delay:v1', title: 'wait a fixed amount of time' },
      { value: 'calendar:v1', title: 'find a specific day or date' }
    ]"
    v-model="createType"
  >
    <template v-slot:prepend>Then</template>
    <template v-slot:append
      ><v-btn @click="create" variant="plain"><v-icon>mdi-plus</v-icon></v-btn></template
    >
  </v-select>
</template>
