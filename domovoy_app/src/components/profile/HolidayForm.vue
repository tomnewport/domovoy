<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { toast } from 'vue-sonner'
import { useHomesStore } from '@/stores/homes'
import { describeRange, todayString, type HolidayDraft, type HolidayGroup } from './holidays'

// Add or edit one holiday. `group` set means editing (with Delete).
const props = defineProps<{
  modelValue: boolean
  initial: HolidayDraft
  group: HolidayGroup | null
  save: (draft: HolidayDraft) => Promise<void>
  remove: (group: HolidayGroup) => Promise<void>
}>()
const emit = defineEmits<{ 'update:modelValue': [open: boolean] }>()

const homesStore = useHomesStore()
const form = ref<VForm | null>(null)
const draft = ref<HolidayDraft>({ ...props.initial })
const busy = ref<null | 'save' | 'delete'>(null)
const error = ref<string | null>(null)

watch(
  () => [props.modelValue, props.initial] as const,
  ([open]) => {
    if (open) {
      draft.value = { ...props.initial, homeIds: [...props.initial.homeIds] }
      error.value = null
    }
  }
)

const today = todayString()
const isPast = computed(() => !!props.group && props.group.to < today)
const summary = computed(() =>
  draft.value.from && draft.value.to && draft.value.from <= draft.value.to
    ? describeRange(draft.value.from, draft.value.to)
    : null
)
const rules = {
  from: [(v: string) => !!v || 'Pick the first day'],
  to: [
    (v: string) => !!v || 'Pick the last day',
    (v: string) => !draft.value.from || v >= draft.value.from || 'Ends before it starts',
    (v: string) => v >= today || 'Must end today or later'
  ],
  homes: [(v: number[]) => v.length > 0 || 'Choose at least one home']
}

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  // With one home the selector is hidden: you're away from it.
  if (!draft.value.homeIds.length) {
    draft.value.homeIds = (homesStore.homes ?? []).map((h) => h.id as number)
  }
  const { valid } = (await form.value?.validate()) ?? { valid: false }
  if (!valid) return
  busy.value = 'save'
  error.value = null
  try {
    await props.save(draft.value)
    toast.success(props.group ? 'Holiday updated' : 'Holiday added')
    close()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Could not save the holiday.'
  } finally {
    busy.value = null
  }
}

async function onDelete() {
  if (!props.group) return
  busy.value = 'delete'
  try {
    await props.remove(props.group)
    toast.success('Holiday deleted')
    close()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Could not delete the holiday.'
  } finally {
    busy.value = null
  }
}
</script>
<template>
  <v-dialog
    :model-value="modelValue"
    max-width="440"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="xl">
      <v-card-item class="px-6 pt-5">
        <v-card-title>{{
          group ? (isPast ? 'Past holiday' : 'Edit holiday') : 'Add a holiday'
        }}</v-card-title>
        <v-card-subtitle v-if="summary">
          {{ summary.text }} · {{ summary.days }} {{ summary.days === 1 ? 'day' : 'days' }}
        </v-card-subtitle>
      </v-card-item>
      <v-card-text class="px-6">
        <p v-if="isPast" class="text-body-2 text-medium-emphasis mb-3">
          {{ group?.note || 'No note' }}. Past holidays can't be changed, only deleted.
        </p>
        <v-form v-else ref="form" @submit.prevent="submit">
          <v-alert
            v-if="error"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-4"
            :text="error"
          />
          <div class="d-flex ga-3">
            <v-text-field
              v-model="draft.from"
              label="First day away"
              type="date"
              variant="outlined"
              :rules="rules.from"
            />
            <v-text-field
              v-model="draft.to"
              label="Last day away"
              type="date"
              variant="outlined"
              :min="draft.from || today"
              :rules="rules.to"
            />
          </div>
          <v-text-field
            v-model="draft.note"
            label="Note (optional)"
            placeholder="e.g. Skiing"
            variant="outlined"
            counter="256"
            maxlength="256"
          />
          <v-select
            v-if="(homesStore.homes?.length ?? 0) > 1"
            v-model="draft.homeIds"
            :items="homesStore.homes ?? []"
            item-title="name"
            item-value="id"
            label="Away from"
            variant="outlined"
            multiple
            chips
            :rules="rules.homes"
          />
          <p class="text-caption text-medium-emphasis">
            Jobs won't be scheduled for you on these days. Ones already assigned stay as they are.
          </p>
        </v-form>
      </v-card-text>
      <v-card-actions class="px-6 pb-5">
        <v-btn
          v-if="group"
          color="error"
          variant="text"
          prepend-icon="mdi-delete-outline"
          :loading="busy === 'delete'"
          :disabled="busy === 'save'"
          @click="onDelete"
        >
          Delete
        </v-btn>
        <v-spacer />
        <v-btn variant="text" :disabled="busy !== null" @click="close">Cancel</v-btn>
        <v-btn
          v-if="!isPast"
          color="primary"
          variant="flat"
          :loading="busy === 'save'"
          :disabled="busy === 'delete'"
          @click="submit"
        >
          {{ group ? 'Save' : 'Add holiday' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
