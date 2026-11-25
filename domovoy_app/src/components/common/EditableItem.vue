<script setup lang="ts">
import { ref, watch } from 'vue'
import { toast } from 'vue-sonner'
const props = defineProps<{
  label: string
  value?: string | number
  onChange: (arg: string) => Promise<void>
  type?: 'text' | 'number'
}>()

// `??`, not `||`: a value of 0 is shown, not left blank.
const text = (v?: string | number) => (v ?? '').toString()

const value = ref<string>(text(props.value))
const saving = ref<boolean>(false)

const open = ref<boolean>(false)
// Follow the saved value (e.g. after a refresh) unless it's being edited.
watch(
  () => props.value,
  (v) => {
    if (!open.value) value.value = text(v)
  }
)
function edit() {
  // Coming back to a field whose save failed keeps what was typed.
  if (open.value) return
  open.value = true
  value.value = text(props.value)
}
function reset() {
  open.value = false
  value.value = text(props.value)
}

async function save() {
  if (value.value === text(props.value)) {
    open.value = false
    return
  }
  saving.value = true
  try {
    await props.onChange(value.value)
    open.value = false
  } catch (err) {
    // Keep the typed value, with its undo button, to retry or revert.
    toast.error(`${props.label} not saved: ${err instanceof Error ? err.message : 'try again'}`)
  } finally {
    saving.value = false
  }
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
    :append-inner-icon="value !== text(props.value) ? 'mdi-undo' : undefined"
    :disabled="saving"
    @click:append-inner="reset"
  >
    <template v-slot:loader>
      <v-progress-linear :active="saving" height="7" indeterminate></v-progress-linear>
    </template>
  </v-text-field>
</template>
