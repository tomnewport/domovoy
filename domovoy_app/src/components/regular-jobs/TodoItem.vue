<script setup lang="ts">
import { computed } from 'vue'
import type { RegularJobDefinition } from '@/stores/regular-job'
import { useQuickClaimStore } from '@/stores/quick-claim'
import { formatNaturalDateInline } from '@/utils/dates'
import { JobClassification } from './utils'

// One job on the task list, kept to three things: a circle to tick it off
// (at its usual points, with a few seconds to undo), its name with one line
// of when and whose, and what it's worth. Everything else (the points
// range, the bonus breakdown, the home, snoozing) is on its card, which
// tapping the job opens.
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
const quickClaim = useQuickClaimStore()

const pending = computed(() => quickClaim.isPending(job.id))
// What ticking it off earns you now: the usual points, plus the bonus for
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
  <v-list-item
    class="todo-item"
    :class="{ 'todo-item--pending': pending }"
    :ripple="!pending"
    @click="pending || onOpen()"
  >
    <template #prepend>
      <!-- Ticked: tap again to undo, like a checklist. -->
      <v-btn
        icon
        variant="text"
        size="small"
        class="todo-item__tick mr-2"
        :class="{ 'todo-item__tick--done': pending }"
        :aria-label="pending ? `Undo ${job.name}` : `Mark ${job.name} done, ${points} points`"
        :aria-pressed="pending"
        @click.stop="pending ? quickClaim.undo(job.id as number) : quickClaim.tick(job)"
      >
        <v-icon :icon="pending ? 'mdi-check-circle' : 'mdi-circle-outline'" size="26" />
      </v-btn>
    </template>

    <v-list-item-title class="todo-item__title">{{ job.name }}</v-list-item-title>
    <v-list-item-subtitle>
      <template v-if="pending">Done</template>
      <template v-else>
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
      </template>
    </v-list-item-subtitle>

    <template #append>
      <span class="todo-item__points text-body-2">+{{ points }}</span>
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
.todo-item__tick {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.todo-item__tick--done {
  color: rgb(var(--v-theme-primary));
}
.todo-item--pending .todo-item__title {
  text-decoration: line-through;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.todo-item__points {
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
