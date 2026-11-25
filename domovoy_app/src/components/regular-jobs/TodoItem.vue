<script setup lang="ts">
import { computed } from 'vue'
import type { RegularJobDefinition } from '@/stores/regular-job'
import { useQuickClaimStore } from '@/stores/quick-claim'
import { formatNaturalDateInline } from '@/utils/dates'
import { JobClassification } from './utils'

// One job on the task list: what it is, when it's due, what it's worth, and
// a ✓ to mark it done there and then, at its usual points (with a few
// seconds to undo). Tapping the job opens its card, to choose the points
// or snooze it.
const {
  job,
  classification,
  mine,
  showHome = false,
  showDate = 'due',
  onOpen
} = defineProps<{
  job: RegularJobDefinition
  classification: JobClassification
  mine: boolean
  showHome?: boolean
  showDate?: 'due' | 'assigned'
  onOpen: () => void
}>()
const quickClaim = useQuickClaimStore()

const pending = computed(() => quickClaim.isPending(job.id))
const fixedValue = computed(() => job.value_min === job.value_max)
const bonus = computed(() => (!mine && job.bonus ? job.bonus : 0))

// Status is always an icon with a word, never colour alone.
const status = computed(() => {
  switch (classification) {
    case JobClassification.URGENT:
      return { label: 'Urgent', icon: 'mdi-alert-octagon', color: 'error' }
    case JobClassification.OVERDUE:
      return { label: 'Overdue', icon: 'mdi-clock-alert-outline', color: 'warning' }
    case JobClassification.PRIORITY:
      return { label: 'Priority', icon: 'mdi-flag', color: 'info' }
    default:
      return null
  }
})

const natural = (iso: string) => formatNaturalDateInline(new Date(iso))
const when = computed(() => {
  if (classification === JobClassification.UNSCHEDULED) return 'Not scheduled'
  if (showDate === 'assigned' && job.next_assigned_date)
    return `Assigned ${natural(job.next_assigned_date)}`
  return job.next_assigned_due_date ? `Due ${natural(job.next_assigned_due_date)}` : ''
})
</script>
<template>
  <v-list-item
    class="todo-item"
    :class="{ 'todo-item--pending': pending }"
    :ripple="!pending"
    @click="pending || onOpen()"
  >
    <v-list-item-title class="todo-item__title">{{ job.name }}</v-list-item-title>
    <v-list-item-subtitle class="todo-item__meta">
      <v-chip
        v-if="status && !pending"
        :color="status.color"
        :prepend-icon="status.icon"
        size="x-small"
        variant="tonal"
        label
        class="mr-1"
      >
        {{ status.label }}
      </v-chip>
      <span v-if="pending">Done · sending in a moment</span>
      <template v-else>
        <span>{{ when }}</span>
        <span v-if="!mine && job.next_assigned_to">
          · <d-user-display variant="short">{{ job.next_assigned_to }}</d-user-display></span
        >
        <span v-if="showHome">
          · <d-home-display>{{ job.home }}</d-home-display></span
        >
      </template>
    </v-list-item-subtitle>

    <template #append>
      <div class="todo-item__points" :class="{ 'text-medium-emphasis': pending }">
        <span class="text-body-2 font-weight-bold">+{{ job.value_default }}</span>
        <span v-if="bonus" class="text-caption todo-item__bonus">+{{ bonus }} bonus</span>
        <span v-else-if="!fixedValue" class="text-caption text-medium-emphasis">
          {{ job.value_min }}–{{ job.value_max }}
        </span>
      </div>
      <v-btn
        v-if="pending"
        variant="text"
        size="small"
        class="ml-1"
        :aria-label="`Undo ${job.name}`"
        @click.stop="quickClaim.undo(job.id as number)"
      >
        Undo
      </v-btn>
      <v-btn
        v-else
        icon
        variant="tonal"
        color="primary"
        size="small"
        class="ml-2"
        :aria-label="`Mark ${job.name} done, ${job.value_default} points`"
        @click.stop="quickClaim.tick(job)"
      >
        <v-icon icon="mdi-check" />
      </v-btn>
    </template>
  </v-list-item>
</template>
<style scoped>
.todo-item__title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Inline, not flex: flex would drop the spaces around each "·". */
.todo-item__meta {
  white-space: normal;
}
.todo-item__meta .v-chip {
  vertical-align: middle;
}
.todo-item--pending .todo-item__title {
  text-decoration: line-through;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.todo-item__points {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-variant-numeric: tabular-nums;
  min-width: 2.5rem;
}
.todo-item__bonus {
  color: rgb(var(--v-theme-success));
}
</style>
