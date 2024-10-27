<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRegularJobStore, type HomeStatistics } from '@/stores/regular-job'
import JobAssignerResult from './JobAssignerResult.vue'

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
          <v-row
            v-for="user of regularJobStore.motivation?.stats.users || []"
            :key="user.id"
            no-gutters
          >
            <v-col cols="2" v-if="user.relative_score > 0">+{{ user.relative_score }}</v-col>
            <v-col cols="2" v-else></v-col>
            <v-col cols="6">{{ user.name }}</v-col>
            <v-col cols="4">
              <v-sparkline color="primary" auto-draw :model-value="user.daily_scores"></v-sparkline
            ></v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </template>
  </v-dialog>
</template>
