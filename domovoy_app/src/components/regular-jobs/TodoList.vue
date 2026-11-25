<script setup lang="ts">
import { useRegularJobStore, type RegularJobDefinition } from '@/stores/regular-job'
import CompleteJobCard from '@/components/regular-jobs/CompleteJobCard.vue'
import TodoItem from '@/components/regular-jobs/TodoItem.vue'
import { computed, ref } from 'vue'
import { useCurrentUser } from '@/lookups/user'
import { getJobClassification, JobClassification } from './utils'
import JobEditor from './JobEditor.vue'

const searchTerm = ref<string | null>(null)
const sortType = ref<'priority' | 'due' | 'assigned'>('priority')

const you = useCurrentUser()
const jobStore = useRegularJobStore()
interface ClassifiedJobDefinition {
  job: RegularJobDefinition
  classification: JobClassification
}

const sections = [
  { classification: JobClassification.URGENT, title: 'Urgent' },
  { classification: JobClassification.PRIORITY, title: 'Priority' },
  { classification: JobClassification.OVERDUE, title: 'Overdue' },
  { classification: JobClassification.ASSIGNED, title: 'Assigned to me' },
  { classification: JobClassification.IN_HOME, title: 'Ready to do' },
  { classification: JobClassification.FUTURE, title: 'Coming up' },
  // No date and nobody assigned: no rules yet, or nobody free to take it.
  // Listed so it can still be found and done.
  { classification: JobClassification.UNSCHEDULED, title: 'Not scheduled' }
]

const matchedJobs = computed(() => {
  const grouped: { [k in JobClassification]: ClassifiedJobDefinition[] } = {
    [JobClassification.UNSCHEDULED]: [],
    [JobClassification.FUTURE]: [],
    [JobClassification.IN_HOME]: [],
    [JobClassification.ASSIGNED]: [],
    [JobClassification.OVERDUE]: [],
    [JobClassification.PRIORITY]: [],
    [JobClassification.URGENT]: []
  }
  return {
    grouped,
    ungrouped: jobStore.definitions
      .filter(
        (job) =>
          searchTerm.value === null ||
          job.name.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
          job.description?.toLowerCase().includes(searchTerm.value.toLowerCase())
      )
      .sort((job1, job2) => {
        // Jobs with no date go last whichever date the list is sorted by.
        const key = sortType.value === 'assigned' ? 'next_assigned_date' : 'next_assigned_due_date'
        const a = job1[key]
        const b = job2[key]
        if (!a || !b) return a ? -1 : b ? 1 : job1.name.localeCompare(job2.name)
        if (sortType.value === 'assigned') return a > b ? -1 : 1
        return a > b ? 1 : -1
      })
      .map((job) => {
        const classification = getJobClassification(job, you.value)
        grouped[classification].push({ job, classification })
        return { job, classification }
      })
  }
})

const useGroups = computed(() => sortType.value === 'priority')

const selected = ref<null | (typeof jobStore.definitions)[number]>(null)
const open = ref<boolean>(false)
</script>
<template>
  <v-toolbar app color="secondary" fixed class="fixed-bar d-flex" title="Tasks">
    <v-menu :close-on-content-click="false">
      <template v-slot:activator="{ props }">
        <v-btn v-bind="props" icon>
          <v-icon>mdi-cog</v-icon>
        </v-btn>
      </template>
      <v-card min-width="300">
        <v-list>
          <v-list-item>
            <v-select
              :items="[
                { title: 'Priority', value: 'priority' },
                { title: 'Assigned date', value: 'assigned' },
                { title: 'Due date', value: 'due' }
              ]"
              v-model="sortType"
              label="Sort by"
            >
            </v-select>
          </v-list-item>
        </v-list>
      </v-card>
    </v-menu>
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
  <!-- Bottom room so the last task can scroll clear of the ✓ button. -->
  <v-list lines="two" class="pa-0 todo-list">
    <v-list-item>
      <v-text-field
        clearable
        variant="outlined"
        prepend-inner-icon="mdi-magnify"
        hide-details
        single-line
        v-model="searchTerm"
      ></v-text-field>
    </v-list-item>
    <template v-if="!jobStore.hasData">
      <!-- First visit, nothing cached yet: hold the list's shape while it loads. -->
      <v-skeleton-loader
        v-for="n in 6"
        :key="`skeleton-${n}`"
        type="list-item-avatar-two-line"
        color="background"
        aria-hidden="true"
      />
    </template>
    <div
      v-else-if="jobStore.fresh && matchedJobs.ungrouped.length === 0"
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
    <template v-if="useGroups">
      <template
        v-for="section in sections.filter(
          ({ classification }) => matchedJobs.grouped[classification].length > 0
        )"
        :key="section.classification"
      >
        <v-list-subheader>{{ section.title }}</v-list-subheader>
        <TodoItem
          :onClick="
            () => {
              selected = match.job
              open = true
            }
          "
          :job="match.job"
          :classification="match.classification"
          v-for="match of matchedJobs.grouped[section.classification]"
          :key="match.job.id || -1"
        ></TodoItem>
      </template>
    </template>
    <template v-if="!useGroups">
      <TodoItem
        :onClick="
          () => {
            selected = match.job
            open = true
          }
        "
        :show-date="sortType === 'assigned' ? 'assigned' : 'due'"
        :job="match.job"
        :classification="match.classification"
        v-for="match of matchedJobs.ungrouped"
        :key="match.job.id || -1"
      ></TodoItem>
    </template>
  </v-list>
</template>
<style scoped>
.todo-list {
  padding-bottom: 88px !important;
}
</style>
