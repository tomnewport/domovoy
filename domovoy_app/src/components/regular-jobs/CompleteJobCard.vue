<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import {
  AlreadyDoneError,
  useRegularJobStore,
  type RegularJobDefinition
} from '@/stores/regular-job'
import { useCurrentUser } from '@/lookups/user'
import { formatNaturalDate } from '@/utils/dates'
const { jobDefinition, onClose } = defineProps<{
  jobDefinition: RegularJobDefinition
  onClose: () => void
}>()
const regularJobStore = useRegularJobStore()
const value = ref<number>(jobDefinition.value_default)

// Which action is running, so its button can spin and the others wait.
const busy = ref<null | 'claim' | 'snooze'>(null)
const snoozingTo = ref<string | null>(null)

// Until this visit's task list has arrived, the job shown may be from the
// cache; hold actions until it's confirmed (usually well under a second).
const syncing = computed(() => !regularJobStore.fresh && regularJobStore.loading)

onMounted(() => {
  // Most people read the card before choosing; fetch the snooze dates now so
  // the menu opens with them ready.
  if (jobDefinition.next_assigned_due_date) regularJobStore.prefetchSnoozeOptions(jobDefinition)
})

const snoozeState = computed(() => regularJobStore.snoozeOptionsFor(jobDefinition))

function onFailure(err: unknown, fallback: string) {
  if (err instanceof AlreadyDoneError) {
    toast.info(`${jobDefinition.name} was already done, so nothing changed.`)
    onClose()
  } else {
    toast.error(err instanceof Error ? err.message : fallback)
  }
}

async function claim() {
  // Ignore a second press while the first is on its way.
  if (busy.value || !jobDefinition.id) return
  busy.value = 'claim'
  try {
    await regularJobStore.claim({ definition: jobDefinition, value: value.value })
    onClose()
  } catch (err) {
    onFailure(err, 'Could not claim this job')
  } finally {
    busy.value = null
  }
}

async function snooze(date: string) {
  if (busy.value) return
  busy.value = 'snooze'
  snoozingTo.value = date
  try {
    await regularJobStore.snooze(jobDefinition, date)
    toast.success(`${jobDefinition.name} snoozed until ${formatNaturalDate(new Date(date))}`)
    onClose()
  } catch (err) {
    onFailure(err, 'Could not snooze this job')
  } finally {
    busy.value = null
    snoozingTo.value = null
  }
}

const me = useCurrentUser()

const mine = computed(() => me.value?.id === jobDefinition.next_assigned_to)
const scheduled = computed(() => !!jobDefinition.next_assigned_due_date)
</script>

<template>
  <v-card>
    <v-card-title class="d-flex"
      ><span>{{ jobDefinition.name }}</span>
      <v-spacer></v-spacer>
      <v-btn
        size="small"
        variant="plain"
        icon
        :to="`/tasks/${jobDefinition.id}/edit`"
        aria-label="Edit job"
        ><v-icon>mdi-pencil</v-icon></v-btn
      ></v-card-title
    >
    <v-card-subtitle class="d-flex">
      <template v-if="scheduled">
        <span
          ><d-user-display>{{ jobDefinition.next_assigned_to }}</d-user-display></span
        >
        <v-spacer></v-spacer>
        <span
          >Due
          <d-date-display variant="natural">{{
            jobDefinition.next_assigned_due_date
          }}</d-date-display></span
        >
      </template>
      <span v-else>Not scheduled: anyone can do it any time</span>
    </v-card-subtitle>

    <v-list>
      <v-list-item v-if="jobDefinition.description">
        {{ jobDefinition.description }}
      </v-list-item>
      <v-list-item v-if="jobDefinition.value_min === jobDefinition.value_max"
        ><template v-slot:prepend> <v-icon icon="mdi-medal"></v-icon> </template
        >{{ jobDefinition.value_default }} points</v-list-item
      >
      <v-list-item v-if="!mine && jobDefinition.bonus"
        ><template v-slot:prepend> <v-icon icon="mdi-cash-clock"></v-icon> </template
        >{{ jobDefinition.bonus }} bonus</v-list-item
      >
    </v-list>
    <v-slider
      v-if="jobDefinition.value_min < jobDefinition.value_max"
      hoist
      step="1"
      thumb-label
      v-model="value"
      :min="jobDefinition.value_min"
      :max="jobDefinition.value_max"
    >
      <template v-slot:prepend>{{ jobDefinition.value_min }}</template>
      <template v-slot:append>{{ jobDefinition.value_max }}</template>
    </v-slider>
    <v-card-actions>
      <v-btn v-on:click="onClose" :disabled="busy !== null">Cancel</v-btn>
      <v-spacer></v-spacer>
      <!-- Snoozing moves a due date; a job without one has nothing to move. -->
      <v-menu v-if="scheduled" location="top end">
        <template v-slot:activator="{ props }">
          <v-btn
            v-bind="props"
            v-on:pointerenter="regularJobStore.prefetchSnoozeOptions(jobDefinition)"
            v-on:focus="regularJobStore.prefetchSnoozeOptions(jobDefinition)"
            color="secondary"
            prepend-icon="mdi-sleep"
            :loading="busy === 'snooze'"
            :disabled="syncing || busy === 'claim'"
            >Snooze</v-btn
          >
        </template>
        <v-list min-width="220" density="comfortable">
          <v-list-subheader>Snooze until</v-list-subheader>
          <template v-if="snoozeState?.options">
            <v-list-item
              v-for="option in snoozeState.options"
              :key="option.label"
              :value="option.date"
              :disabled="busy !== null"
              v-on:click="snooze(option.date)"
            >
              <v-list-item-title
                ><d-date-display variant="natural">{{
                  option.date
                }}</d-date-display></v-list-item-title
              >
              <template v-if="snoozingTo === option.date" v-slot:append>
                <v-progress-circular indeterminate size="18" width="2" />
              </template>
            </v-list-item>
            <v-list-item v-if="snoozeState.options.length === 0" disabled>
              <v-list-item-title>No later dates available</v-list-item-title>
            </v-list-item>
          </template>
          <v-list-item
            v-else-if="snoozeState?.error"
            prepend-icon="mdi-refresh"
            v-on:click.stop="regularJobStore.prefetchSnoozeOptions(jobDefinition)"
          >
            <v-list-item-title>Couldn't load dates</v-list-item-title>
            <v-list-item-subtitle>Tap to try again</v-list-item-subtitle>
          </v-list-item>
          <template v-else>
            <!-- Still on its way: same shape as the dates, so nothing jumps. -->
            <v-skeleton-loader
              v-for="n in 4"
              :key="n"
              type="list-item"
              color="transparent"
              aria-hidden="true"
            />
          </template>
        </v-list>
      </v-menu>
      <v-btn
        v-on:click="claim"
        prepend-icon="mdi-check"
        color="primary"
        :loading="busy === 'claim' || syncing"
        :disabled="busy === 'snooze'"
        >Claim</v-btn
      >
    </v-card-actions>
  </v-card>
</template>
