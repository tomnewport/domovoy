<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRegularJobStore, type HomeStatistics } from '@/stores/regular-job'
import JobAssignerResult from './JobAssignerResult.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import { memberColors } from '@/utils/memberColors'

const regularJobStore = useRegularJobStore()

const open = ref<boolean>(false)

watch(regularJobStore, () => {
  if (regularJobStore.motivation?.open) open.value = true
})

watch(open, (newValue) => {
  if (!newValue) regularJobStore.closeMotivation()
})

const self = computed((): null | HomeStatistics['users'][number] => {
  if (!regularJobStore.motivation) return null

  return (
    (regularJobStore.motivation.stats.users || []).find(
      ({ id }) => id === regularJobStore.motivation?.stats.self
    ) || null
  )
})

const weekly = computed(
  (): number =>
    [...(self?.value?.daily_scores || [])].slice(-7).reduce((acc, val) => acc + val, 0) || 0
)
const daily = computed((): number =>
  self.value ? [...(self.value.daily_scores || [])].slice(-1)[0] : 0
)

// Everyone's sparkline is drawn against the same top value, so a taller line
// really is more points.
const users = computed(() => regularJobStore.motivation?.stats.users || [])
const sharedMax = computed(() => Math.max(1, ...users.value.flatMap((u) => u.daily_scores)))
const colors = computed(() => memberColors(users.value.map((u) => u.id)))
</script>
<template>
  <v-dialog
    :transition="open ? 'dialog-bottom-transition' : 'dialog-top-transition'"
    style="max-width: 30rem"
    v-model="open"
  >
    <template v-slot:default>
      <v-card>
        <v-card-title class="d-flex">
          <span style="margin-top: 0.5rem">Well done!</span>
          <v-spacer></v-spacer>
          <v-btn icon variant="plain" @click="open = false"><v-icon>mdi-close</v-icon></v-btn>
        </v-card-title>
        <v-card-text>
          <v-row no-gutters>
            <v-col class="text-h2" cols="6">+{{ regularJobStore.motivation?.valueChange }} </v-col>
            <v-col class="text-right" cols="6">
              <v-icon color="success" icon="mdi-medal" size="88"></v-icon>
            </v-col>
            <v-col cols="6"> +{{ (daily || 0).toString() }} today</v-col>
            <v-col class="text-right" cols="6"> +{{ (weekly || 0).toString() }} this week </v-col>
          </v-row>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-text>
          <JobAssignerResult
            v-if="regularJobStore.motivation?.result"
            :value="regularJobStore.motivation.result"
          />
        </v-card-text>
        <v-divider></v-divider>
        <v-card-text>
          <div class="d-flex justify-space-between text-caption text-medium-emphasis mb-2">
            <span>Points per day, last {{ users[0]?.daily_scores.length ?? 30 }} days</span>
            <span>Same scale: 0–{{ sharedMax }}</span>
          </div>
          <div v-for="user of users" :key="user.id" class="d-flex align-center ga-3 py-1">
            <span class="score text-body-2 text-medium-emphasis">
              <template v-if="user.relative_score > 0">+{{ user.relative_score }}</template>
            </span>
            <span
              class="name text-body-2"
              :class="{ 'font-weight-bold': user.id === regularJobStore.motivation?.stats.self }"
            >
              {{ user.name_short
              }}<template v-if="user.id === regularJobStore.motivation?.stats.self">
                (you)</template
              >
            </span>
            <Sparkline
              class="flex-grow-1"
              :values="user.daily_scores"
              :max="sharedMax"
              :color="colors.get(user.id) ?? '#9c9c9c'"
              :label="`${user.name}: ${user.daily_scores.reduce((a, b) => a + b, 0)} points in the last ${user.daily_scores.length} days`"
            />
          </div>
        </v-card-text>
      </v-card>
    </template>
  </v-dialog>
</template>

<style scoped>
.score {
  width: 2.5rem;
  flex: none;
}
.name {
  width: 6rem;
  flex: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
