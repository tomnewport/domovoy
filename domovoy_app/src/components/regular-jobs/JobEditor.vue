<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import InstanceViewer from './InstanceViewer.vue'
import { useRoute, useRouter } from 'vue-router'
import { useRegularJobStore, type EditJobDefinition, type Ruleset } from '@/stores/regular-job'
import RulesEditor from './RulesEditor.vue'
const route = useRoute()
const router = useRouter()
const regularJobStore = useRegularJobStore()

const { backLink } = defineProps<{ backLink: string }>()

const open = ref<boolean>(route.params.jobId !== undefined)
const savingCriticality = ref<boolean>(false)

onMounted(() => regularJobStore.reload())

watch(route, () => {
  regularJobStore.reload()
  if (route.params.jobId) open.value = true
  else open.value = false
})
watch(open, (newValue) => {
  if (!newValue) router.push(backLink)
})

const job = computed(() => {
  if (!route.params.jobId) return null
  const jobId = typeof route.params.jobId === 'string' ? route.params.jobId : route.params.jobId[0]
  const job = regularJobStore.definitions.find((job) => job.id === parseInt(jobId))
  return job || null
})
const criticality = ref<undefined | string>(job.value?.criticality)

watch(job, () => {
  const jobCriticality = job.value?.criticality
  if (typeof jobCriticality === 'string') {
    criticality.value = jobCriticality
  } else {
    criticality.value = undefined
  }
})

watch(criticality, async () => {
  const jobCriticality = criticality.value
  // Only a change someone made: not the value arriving as the job loads.
  if (typeof jobCriticality !== 'string' || !job.value || jobCriticality === job.value.criticality)
    return
  savingCriticality.value = true
  try {
    await update({ criticality: jobCriticality as 'L' | 'M' | 'H' })
  } catch (err) {
    criticality.value = job.value?.criticality
    toast.error(`Criticality not saved: ${err instanceof Error ? err.message : 'try again'}`)
  } finally {
    savingCriticality.value = false
  }
})

async function update(changeObj: Partial<EditJobDefinition>) {
  if (job.value?.id) await regularJobStore.editDefinition(job.value.id, changeObj)
}

// The rule editors don't handle failures themselves: report them here.
async function saveRules(rules: Ruleset) {
  try {
    await update({ rules })
  } catch (err) {
    toast.error(`Schedule not saved: ${err instanceof Error ? err.message : 'try again'}`)
  }
}
</script>
<template>
  <v-dialog v-if="job" v-model="open" fullscreen scrollable>
    <template v-slot:default>
      <v-toolbar color="secondary"
        ><v-btn icon :to="backLink"><v-icon>mdi-arrow-left</v-icon></v-btn
        ><v-toolbar-title>{{ job.name }}</v-toolbar-title></v-toolbar
      >
      <v-card :style="{ paddingBottom: '100px' }">
        <v-container>
          <v-expansion-panels>
            <v-expansion-panel>
              <v-expansion-panel-title> Settings </v-expansion-panel-title>
              <v-expansion-panel-text>
                <d-editable-item
                  label="Name"
                  :onChange="(name: string) => update({ name })"
                  :value="job.name"
                />
                <d-editable-item
                  :onChange="(description: string) => update({ description })"
                  label="Description"
                  :value="job.description"
                />
                <v-row>
                  <v-col>
                    <d-editable-item
                      :onChange="(value: string) => update({ open_for_days: parseInt(value) })"
                      label="Open for (days)"
                      type="number"
                      :value="job.open_for_days"
                    />
                  </v-col>
                  <v-col>
                    <d-editable-item
                      :onChange="(value: string) => update({ value_default: parseInt(value) })"
                      label="Default value"
                      type="number"
                      :value="job.value_default"
                    />
                  </v-col>
                </v-row>
                <v-row>
                  <v-col>
                    <d-editable-item
                      :onChange="(value: string) => update({ value_min: parseInt(value) })"
                      label="Minimum value"
                      type="number"
                      :value="job.value_min"
                    />
                  </v-col>
                  <v-col>
                    <d-editable-item
                      :onChange="(value: string) => update({ value_max: parseInt(value) })"
                      label="Maximum value"
                      type="number"
                      :value="job.value_max"
                    />
                  </v-col>
                </v-row>
                <v-select
                  label="Criticality"
                  item-title="label"
                  item-value="value"
                  variant="underlined"
                  v-model="criticality"
                  :items="[
                    { label: 'Low - schedule when available', value: 'L' },
                    { label: 'Medium - try to find earlier alternative', value: 'M' },
                    { label: 'High - hard deadline, priority in app', value: 'H' }
                  ]"
                >
                  <template v-slot:loader>
                    <v-progress-linear
                      :active="savingCriticality"
                      height="7"
                      indeterminate
                    ></v-progress-linear>
                  </template>
                </v-select>
              </v-expansion-panel-text>
            </v-expansion-panel>
            <v-expansion-panel>
              <v-expansion-panel-title>Rules</v-expansion-panel-title>
              <v-expansion-panel-text class="pa-0">
                <RulesEditor v-if="job" :value="job.rules" :onChange="saveRules"></RulesEditor>
              </v-expansion-panel-text>
            </v-expansion-panel>
            <v-expansion-panel v-if="job?.id">
              <v-expansion-panel-title>History</v-expansion-panel-title>
              <v-expansion-panel-text><InstanceViewer :job-id="job.id" /></v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-container>
      </v-card>
    </template>
  </v-dialog>
</template>
