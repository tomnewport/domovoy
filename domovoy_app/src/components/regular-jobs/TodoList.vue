<script setup lang="ts">
import { useRegularJobStore, type RegularJobDefinition } from '@/stores/regular-job'
import { useHomesStore } from '@/stores/homes'
import CompleteJobCard from '@/components/regular-jobs/CompleteJobCard.vue'
import TodoItem from '@/components/regular-jobs/TodoItem.vue'
import { computed, ref } from 'vue'
import { useCurrentUser } from '@/lookups/user'
import { formatNaturalDateInline } from '@/utils/dates'
import { getJobClassification, JobClassification } from './utils'
import JobEditor from './JobEditor.vue'

// The task list, led by what can be done now: your jobs, then others' that
// anyone can pick up. Later and unscheduled jobs are folded away.

const searchTerm = ref<string | null>(null)
const sortType = ref<'priority' | 'due' | 'assigned'>('priority')

const you = useCurrentUser()
const jobStore = useRegularJobStore()
const homesStore = useHomesStore()

interface Classified {
  job: RegularJobDefinition
  classification: JobClassification
  mine: boolean
}

// Most pressing first within a section, then by due date.
const SEVERITY: Partial<Record<JobClassification, number>> = {
  [JobClassification.URGENT]: 0,
  [JobClassification.OVERDUE]: 1,
  [JobClassification.PRIORITY]: 2
}
const severity = (c: Classified) => SEVERITY[c.classification] ?? 3
const dueOf = (c: Classified) => c.job.next_assigned_due_date ?? ''

const matched = computed((): Classified[] => {
  const term = searchTerm.value?.toLowerCase().trim()
  return jobStore.definitions
    .filter(
      (job) =>
        !term ||
        job.name.toLowerCase().includes(term) ||
        job.description?.toLowerCase().includes(term)
    )
    .map((job) => ({
      job,
      classification: getJobClassification(job, you.value),
      mine: !!you.value && job.next_assigned_to === you.value.id
    }))
})

const sections = computed(() => {
  const yours: Classified[] = []
  const others: Classified[] = []
  const later: Classified[] = []
  const unscheduled: Classified[] = []
  for (const c of matched.value) {
    if (c.classification === JobClassification.UNSCHEDULED) unscheduled.push(c)
    else if (c.classification === JobClassification.FUTURE) later.push(c)
    else if (c.mine) yours.push(c)
    else others.push(c)
  }
  const byUrgency = (a: Classified, b: Classified) =>
    severity(a) - severity(b) || dueOf(a).localeCompare(dueOf(b))
  return {
    yours: yours.sort(byUrgency),
    others: others.sort(byUrgency),
    later: later.sort((a, b) => dueOf(a).localeCompare(dueOf(b))),
    unscheduled: unscheduled.sort((a, b) => a.job.name.localeCompare(b.job.name))
  }
})

// Your next job, for when there's nothing of yours to do now.
const yourNext = computed(() => {
  const job = sections.value.later.find((c) => c.mine)?.job
  if (!job?.next_assigned_due_date) return null
  return `${job.name}, due ${formatNaturalDateInline(new Date(job.next_assigned_due_date))}`
})

// The flat list, for the date sorts. Jobs with no date go last.
const flat = computed(() => {
  const key = sortType.value === 'assigned' ? 'next_assigned_date' : 'next_assigned_due_date'
  return [...matched.value].sort((x, y) => {
    const a = x.job[key]
    const b = y.job[key]
    if (!a || !b) return a ? -1 : b ? 1 : x.job.name.localeCompare(y.job.name)
    return sortType.value === 'assigned' ? b.localeCompare(a) : a.localeCompare(b)
  })
})

const searching = computed(() => !!searchTerm.value?.trim())
const showLater = ref(false)
const showUnscheduled = ref(false)
const showHome = computed(() => (homesStore.homes?.length ?? 0) > 1)

const selected = ref<null | RegularJobDefinition>(null)
const open = ref<boolean>(false)
function openCard(job: RegularJobDefinition) {
  selected.value = job
  open.value = true
}
</script>
<template>
  <v-toolbar app color="secondary" fixed class="fixed-bar" title="Tasks" />
  <JobEditor back-link="/tasks" />
  <v-dialog v-model="open">
    <CompleteJobCard
      v-if="selected"
      :job-definition="selected"
      :on-close="
        () => {
          selected = null
          open = false
        }
      "
    />
  </v-dialog>

  <div class="todo px-4 pt-3">
    <v-text-field
      v-model="searchTerm"
      clearable
      variant="outlined"
      density="comfortable"
      prepend-inner-icon="mdi-magnify"
      placeholder="Search jobs"
      aria-label="Search jobs"
      hide-details
      single-line
    />
    <v-chip-group
      v-model="sortType"
      mandatory
      selected-class="text-primary"
      class="mt-1"
      aria-label="Sort tasks by"
    >
      <v-chip value="priority" size="small" filter variant="outlined">What to do now</v-chip>
      <v-chip value="due" size="small" filter variant="outlined">Due date</v-chip>
      <v-chip value="assigned" size="small" filter variant="outlined">Recently assigned</v-chip>
    </v-chip-group>
  </div>

  <v-list lines="two" class="pa-0 todo-list" bg-color="transparent">
    <template v-if="!jobStore.hasData">
      <!-- First visit, nothing cached yet: hold the list's shape while it loads. -->
      <v-skeleton-loader
        v-for="n in 6"
        :key="`skeleton-${n}`"
        type="list-item-two-line"
        color="background"
        aria-hidden="true"
      />
    </template>
    <div
      v-else-if="jobStore.fresh && matched.length === 0"
      class="d-flex flex-column align-center text-center pa-8 text-medium-emphasis"
    >
      <v-icon size="48" class="mb-3">{{ searchTerm ? 'mdi-magnify-close' : 'mdi-broom' }}</v-icon>
      <template v-if="searchTerm">
        <div class="text-subtitle-1">No tasks match “{{ searchTerm }}”</div>
      </template>
      <template v-else>
        <div class="text-subtitle-1">Nothing on the list</div>
        <div class="text-body-2">Jobs from your homes appear here once they're scheduled.</div>
      </template>
    </div>

    <template v-else-if="sortType === 'priority'">
      <!-- Yours: always shown, so an empty list says you're done, not lost. -->
      <template v-if="!searching || sections.yours.length">
        <v-list-subheader>Yours</v-list-subheader>
        <TodoItem
          v-for="c of sections.yours"
          :key="c.job.id ?? -1"
          :job="c.job"
          :classification="c.classification"
          :mine="c.mine"
          :show-home="showHome"
          :on-open="() => openCard(c.job)"
        />
        <div
          v-if="!sections.yours.length"
          class="d-flex align-center ga-3 px-4 pb-3 text-body-2 text-medium-emphasis"
        >
          <v-icon icon="mdi-check-circle-outline" color="success" />
          <span>
            Nothing of yours to do right now.
            <template v-if="yourNext">Next: {{ yourNext }}.</template>
          </span>
        </div>
      </template>

      <template v-if="sections.others.length">
        <v-list-subheader>Up for grabs</v-list-subheader>
        <TodoItem
          v-for="c of sections.others"
          :key="c.job.id ?? -1"
          :job="c.job"
          :classification="c.classification"
          :mine="c.mine"
          :show-home="showHome"
          :on-open="() => openCard(c.job)"
        />
      </template>

      <template v-if="sections.later.length">
        <v-list-item
          class="todo-fold"
          :aria-expanded="showLater || searching"
          :disabled="searching"
          @click="showLater = !showLater"
        >
          <v-list-item-title class="text-body-2 text-medium-emphasis">
            Coming up · {{ sections.later.length }}
          </v-list-item-title>
          <template #append>
            <v-icon
              v-if="!searching"
              :icon="showLater ? 'mdi-chevron-up' : 'mdi-chevron-down'"
              size="20"
            />
          </template>
        </v-list-item>
        <template v-if="showLater || searching">
          <TodoItem
            v-for="c of sections.later"
            :key="c.job.id ?? -1"
            :job="c.job"
            :classification="c.classification"
            :mine="c.mine"
            :show-home="showHome"
            :on-open="() => openCard(c.job)"
          />
        </template>
      </template>

      <template v-if="sections.unscheduled.length">
        <v-list-item
          class="todo-fold"
          :aria-expanded="showUnscheduled || searching"
          :disabled="searching"
          @click="showUnscheduled = !showUnscheduled"
        >
          <v-list-item-title class="text-body-2 text-medium-emphasis">
            Not scheduled · {{ sections.unscheduled.length }}
          </v-list-item-title>
          <template #append>
            <v-icon
              v-if="!searching"
              :icon="showUnscheduled ? 'mdi-chevron-up' : 'mdi-chevron-down'"
              size="20"
            />
          </template>
        </v-list-item>
        <template v-if="showUnscheduled || searching">
          <TodoItem
            v-for="c of sections.unscheduled"
            :key="c.job.id ?? -1"
            :job="c.job"
            :classification="c.classification"
            :mine="c.mine"
            :show-home="showHome"
            :on-open="() => openCard(c.job)"
          />
        </template>
      </template>
    </template>

    <template v-else>
      <TodoItem
        v-for="c of flat"
        :key="c.job.id ?? -1"
        :job="c.job"
        :classification="c.classification"
        :mine="c.mine"
        :show-home="showHome"
        :show-date="sortType === 'assigned' ? 'assigned' : 'due'"
        :on-open="() => openCard(c.job)"
      />
    </template>
  </v-list>
</template>
<style scoped>
.todo-list {
  padding-bottom: 24px !important;
}
.todo-fold {
  min-height: 44px;
}
/* A folded section while searching is open, not greyed out. */
.todo-fold.v-list-item--disabled {
  opacity: 1;
}
</style>
