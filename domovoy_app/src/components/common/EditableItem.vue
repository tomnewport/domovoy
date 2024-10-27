<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{
  label: string
  value?: string | number
  onChange: (arg: string) => Promise<void>
  type?: 'text' | 'number'
}>()

const value = ref<string>((props.value || '').toString())
const saving = ref<boolean>(false)

const open = ref<boolean>(false)
function edit() {
  open.value = true
  value.value = (props.value || '').toString()
}
function reset() {
  open.value = false
  value.value = (props.value || '').toString()
}

async function save() {
  saving.value = true
  if (value.value != props.value) {
    await props.onChange(value.value)
  }
  saving.value = false
  open.value = false
}
</script>
<template>
  <v-text-field
    :type="props.type"
    v-on:focus="edit"
    v-on:blur="save"
    :readonly="!open"
    variant="underlined"
    :label="props.label"
    v-model="value"
    :append-inner-icon="value != props.value ? 'mdi-undo' : undefined"
    :disabled="saving"
    @click:append-inner="reset"
  >
    <template v-slot:loader>
      <v-progress-linear :active="saving" height="7" indeterminate></v-progress-linear>
    </template>
  </v-text-field>
</template>
