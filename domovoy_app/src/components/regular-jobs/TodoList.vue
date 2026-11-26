<script setup lang="ts">
import { useRegularJobStore, type RegularJobDefinition } from '@/stores/regular-job'
import CompleteJobCard from '@/components/regular-jobs/CompleteJobCard.vue'
import TodoItem from '@/components/regular-jobs/TodoItem.vue'
import TodoItemClassic from '@/components/regular-jobs/TodoItemClassic.vue'
import { computed, ref, watch } from 'vue'
import { useCurrentUser } from '@/lookups/user'
import { formatNaturalDateInline } from '@/utils/dates'
import { readPreference, writePreference } from '@/utils/preferences'
import { getJobClassification, JobClassification } from './utils'
import JobEditor from './JobEditor.vue'

// The task list, in one of two layouts chosen per device:
// - Simple: led by what can be done now (your jobs, then others' that anyone
//   can pick up), with later and unscheduled jobs folded away.
// - Classic: the original, grouped by how pressing each job is.
// Search stays pinned under the toolbar: people often do a job that isn't
// at the top of the list and look it up to mark it done.

const LAYOUTS = ['classic', 'simple'] as const
type Layout = (typeof LAYOUTS)[number]
const layout = ref<Layout>(readPreference('tasks-layout', LAYOUTS, 'classic'))
watch(layout, (value) => writePreference('tasks-layout', value))
const LAYOUT_OPTIONS: { value: Layout; title: string; subtitle: string }[] = [
  { value: 'classic', title: 'Classic', subtitle: 'Grouped by how pressing' },
  { value: 'simple', title: 'Simple', subtitle: 'Yours, then up for grabs' }
]

const searchTerm = ref<string | null>(null)
const sortType = ref<'priority' | 'due' | 'assigned'>('priority')

const you = useCurrentUser()
const jobStore = useRegularJobStore()

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

// One list by a date: due soonest first, or assigned most recently first.
// Jobs with no date go last.
function flatBy(key: 'next_assigned_date' | 'next_assigned_due_date') {
  return [...matched.value].sort((x, y) => {
    const a = x.job[key]
    const b = y.job[key]
    if (!a || !b) return a ? -1 : b ? 1 : x.job.name.localeCompare(y.job.name)
    return key === 'next_assigned_date' ? b.localeCompare(a) : a.localeCompare(b)
  })
}
const flat = computed(() =>
  flatBy(sortType.value === 'assigned' ? 'next_assigned_date' : 'next_assigned_due_date')
)

// Classic: a section per classification, most pressing first, each by due date.
const CLASSIC_SECTIONS = [
  { classification: JobClassification.URGENT, title: 'Urgent' },
  { classification: JobClassification.PRIORITY, title: 'Priority' },
  { classification: JobClassification.OVERDUE, title: 'Overdue' },
  { classification: JobClassification.ASSIGNED, title: 'Assigned to me' },
  { classification: JobClassification.IN_HOME, title: 'Ready to do' },
  { classification: JobClassification.FUTURE, title: 'Coming up' },
  { classification: JobClassification.UNSCHEDULED, title: 'Not scheduled' }
]
const classicSections = computed(() =>
  CLASSIC_SECTIONS.map((section) => ({
    ...section,
    jobs: flatBy('next_assigned_due_date').filter(
      (c) => c.classification === section.classification
    )
  })).filter((section) => section.jobs.length > 0)
)

const searching = computed(() => !!searchTerm.value?.trim())
const showLater = ref(false)
const showUnscheduled = ref(false)
const SORTS = [
  { value: 'priority', title: 'What to do now' },
  { value: 'due', title: 'Due date' },
  { value: 'assigned', title: 'Recently assigned' }
] as const

const selected = ref<null | RegularJobDefinition>(null)
const open = ref<boolean>(false)
function openCard(job: RegularJobDefinition) {
  selected.value = job
  open.value = true
}
</script>
<template>
  <v-toolbar app color="secondary" fixed class="fixed-bar" title="Tasks" extended>
    <v-menu :close-on-content-click="false">
      <template #activator="{ props }">
        <v-btn v-bind="props" icon aria-label="List options">
          <v-icon icon="mdi-tune-variant" />
        </v-btn>
      </template>
      <v-list density="comfortable" min-width="240">
        <v-list-subheader>Sort by</v-list-subheader>
        <v-list-item
          v-for="sort in SORTS"
          :key="sort.value"
          :active="sortType === sort.value"
          :title="sort.title"
          @click="sortType = sort.value"
        >
          <template #append>
            <v-icon v-if="sortType === sort.value" icon="mdi-check" size="18" />
          </template>
        </v-list-item>
        <v-divider class="my-1" />
        <v-list-subheader>Layout</v-list-subheader>
        <v-list-item
          v-for="option in LAYOUT_OPTIONS"
          :key="option.value"
          :active="layout === option.value"
          :title="option.title"
          :subtitle="option.subtitle"
          @click="layout = option.value"
        >
          <template #append>
            <v-icon v-if="layout === option.value" icon="mdi-check" size="18" />
          </template>
        </v-list-item>
      </v-list>
    </v-menu>
    <template #extension>
      <!-- Pinned with the toolbar, so it's there wherever the list is scrolled. -->
      <v-text-field
        v-model="searchTerm"
        clearable
        variant="solo"
        bg-color="surface"
        density="compact"
        flat
        rounded
        prepend-inner-icon="mdi-magnify"
        placeholder="Search jobs"
        aria-label="Search jobs"
        hide-details
        single-line
        class="mx-4"
        @keydown.escape="searchTerm = null"
      />
    </template>
  </v-toolbar>
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

  <div v-if="sortType !== 'priority'" class="px-4 pt-2 text-body-medium text-medium-emphasis">
    Sorted by {{ SORTS.find((s) => s.value === sortType)?.title.toLowerCase() }}
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
        <div class="text-title-medium">No tasks match “{{ searchTerm }}”</div>
      </template>
      <template v-else>
        <div class="text-title-medium">Nothing on the list</div>
        <div class="text-body-medium">Jobs from your homes appear here once they're scheduled.</div>
      </template>
    </div>

    <template v-else-if="sortType === 'priority' && layout === 'classic'">
      <template v-for="section in classicSections" :key="section.classification">
        <v-list-subheader>{{ section.title }}</v-list-subheader>
        <TodoItemClassic
          v-for="c of section.jobs"
          :key="c.job.id ?? -1"
          :job="c.job"
          :classification="c.classification"
          :on-click="() => openCard(c.job)"
        />
      </template>
    </template>

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
          :on-open="() => openCard(c.job)"
        />
        <div
          v-if="!sections.yours.length"
          class="d-flex align-center ga-3 px-4 pb-3 text-body-medium text-medium-emphasis"
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
          <v-list-item-title class="text-body-medium text-medium-emphasis">
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
          <v-list-item-title class="text-body-medium text-medium-emphasis">
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
            :on-open="() => openCard(c.job)"
          />
        </template>
      </template>
    </template>

    <template v-else-if="layout === 'classic'">
      <TodoItemClassic
        v-for="c of flat"
        :key="c.job.id ?? -1"
        :job="c.job"
        :classification="c.classification"
        :show-date="sortType === 'assigned' ? 'assigned' : 'due'"
        :on-click="() => openCard(c.job)"
      />
    </template>
    <template v-else>
      <TodoItem
        v-for="c of flat"
        :key="c.job.id ?? -1"
        :job="c.job"
        :classification="c.classification"
        :mine="c.mine"
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
