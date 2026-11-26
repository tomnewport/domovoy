<script setup lang="ts">
import { computed } from 'vue'
import type { RegularJobDefinition } from '@/stores/regular-job'
import { formatNaturalDateInline } from '@/utils/dates'
import { JobClassification } from './utils'

// One job on the task list: its name, one line of when and whose, and what
// it's worth. Tapping it opens its card, where it's marked done (jobs are
// done one at a time, so that's a deliberate step) or snoozed, and which
// has the rest: the points range, the bonus breakdown, the home.
const {
  job,
  classification,
  mine,
  showDate = 'due',
  onOpen
} = defineProps<{
  job: RegularJobDefinition
  classification: JobClassification
  mine: boolean
  showDate?: 'due' | 'assigned'
  onOpen: () => void
}>()
// What doing it earns you now: the usual points, plus the bonus for
// picking up someone else's late job.
const points = computed(() => job.value_default + (!mine && job.bonus ? job.bonus : 0))

const natural = (iso: string) => formatNaturalDateInline(new Date(iso))

// One line: when, and whose if not yours. A status is an icon and a word.
const line = computed(() => {
  const due = job.next_assigned_due_date
  if (classification === JobClassification.UNSCHEDULED)
    return { icon: null, color: null, text: 'Not scheduled' }
  if (showDate === 'assigned' && job.next_assigned_date)
    return { icon: null, color: null, text: `Assigned ${natural(job.next_assigned_date)}` }
  if (!due) return { icon: null, color: null, text: '' }
  switch (classification) {
    case JobClassification.URGENT:
      return { icon: 'mdi-alert-octagon', color: 'error', text: `Urgent · due ${natural(due)}` }
    case JobClassification.OVERDUE:
      // "since Monday", not "since this Monday".
      return {
        icon: 'mdi-clock-alert-outline',
        color: 'warning',
        text: `Overdue since ${natural(due).replace(/^this /, '')}`
      }
    case JobClassification.PRIORITY:
      return { icon: 'mdi-flag', color: 'info', text: `Priority · due ${natural(due)}` }
    default:
      return { icon: null, color: null, text: `Due ${natural(due)}` }
  }
})
</script>
<template>
  <v-list-item class="todo-item" @click="onOpen()">
    <v-list-item-title class="todo-item__title">{{ job.name }}</v-list-item-title>
    <v-list-item-subtitle>
      <v-icon
        v-if="line.icon"
        :icon="line.icon"
        :color="line.color ?? undefined"
        size="14"
        class="todo-item__status"
      />
      {{ line.text
      }}<template v-if="!mine && job.next_assigned_to">
        · <d-user-display variant="short">{{ job.next_assigned_to }}</d-user-display>
      </template>
    </v-list-item-subtitle>

    <template #append>
      <span class="todo-item__points text-body-medium">+{{ points }}</span>
    </template>
  </v-list-item>
</template>
<style scoped>
.todo-item__title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.todo-item__status {
  vertical-align: -2px;
  margin-right: 2px;
}
.todo-item__points {
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
