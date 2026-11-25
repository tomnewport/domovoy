<script setup lang="ts">
import { ref, watch } from 'vue'
import { useHomesStore } from '@/stores/homes'
import type { SubmitEventPromise } from 'vuetify'
import { client, getHeaders } from '@/services/domovoy'
import { apiErrorMessage } from '@/services/domovoy/errors'

const homesStore = useHomesStore()

const props = defineProps<{ homeId?: string | string[]; onChange: () => Promise<void> }>()

const home = ref<string>('')
const name = ref<string>('')
const description = ref<string>('')
const value_default = ref<string>('')
const value_min = ref<string>('')
const value_max = ref<string>('')
const customValue = ref<boolean>(false)
const valid = ref<boolean>(false)
const open = ref<boolean>(false)

watch(value_default, (newValue) => {
  if (!customValue.value || !value_min.value) {
    value_min.value = newValue
  }
  if (!customValue.value || !value_max.value) {
    value_max.value = newValue
  }
})

const saving = ref(false)
const error = ref<string | null>(null)

async function send(event: SubmitEventPromise) {
  // Only send a valid form, and only once.
  if (saving.value || !(await event).valid) return
  saving.value = true
  error.value = null
  try {
    const result = await client.POST('/api/regular_jobs/v1/definitions', {
      headers: getHeaders(),
      params: {
        query: {
          home_id: parseInt(
            (typeof props.homeId == 'string' ? props.homeId : (props.homeId || [])[0]) || home.value
          )
        }
      },
      body: {
        name: name.value,
        description: description.value,
        value_default: parseInt(value_default.value),
        value_min: parseInt(customValue.value ? value_min.value : value_default.value),
        value_max: parseInt(customValue.value ? value_max.value : value_default.value)
      }
    })
    if (!result.response.ok) {
      // Keep what was entered, so it can be fixed and sent again.
      error.value = apiErrorMessage(result.error, 'Could not create the job.')
      return
    }
    name.value = ''
    description.value = ''
    value_default.value = ''
    value_min.value = ''
    value_max.value = ''
    await props.onChange()
    open.value = false
  } catch {
    error.value = 'Could not reach the server. Check your connection and try again.'
  } finally {
    saving.value = false
  }
}

const rules = {
  required: (value: string) => !!value || 'This field is required',
  gteMin: (value: string) =>
    parseInt(value) >= parseInt(value_min.value) ||
    `Must be larger than minimum (${value_min.value})`,
  lteMax: (value: string) =>
    parseInt(value) <= parseInt(value_max.value) ||
    `Must be smaller than maximum (${value_max.value})`,
  lte1000: (value: string) => parseInt(value) <= 1000 || 'Must be smaller than 1000',
  gte0: (value: string) => parseInt(value) >= 0 || 'Must be larger than 0'
}
</script>
<template>
  <div class="pa-4 text-center">
    <v-dialog scrollable fullscreen v-model="open">
      <template v-slot:activator="{ props: activatorProps }">
        <v-btn color="surface-variant" icon v-bind="activatorProps"
          ><v-icon>mdi-plus</v-icon></v-btn
        >
      </template>

      <template v-slot:default="{ isActive }">
        <v-form @submit.prevent="send" v-model="valid">
          <v-card prepend-icon="mdi-plus" title="Create job">
            <v-divider></v-divider>

            <v-card-text class="px-4" style="height: 300px">
              <v-select
                v-model="home"
                v-if="props.homeId === undefined"
                label="Select"
                :items="homesStore.homes || []"
                item-title="name"
                item-value="id"
                variant="underlined"
              ></v-select>
              <v-text-field
                v-model="name"
                :rules="[rules.required]"
                label="Job name"
              ></v-text-field>
              <v-textarea
                v-model="description"
                :rules="[rules.required]"
                label="Job description"
              ></v-textarea>
              <v-text-field
                type="number"
                v-model="value_default"
                :rules="[rules.gte0, rules.gteMin, rules.lte1000, rules.lteMax, rules.required]"
                :label="customValue ? 'Default value' : 'Value'"
              ></v-text-field>
              <v-switch label="Job value can change" v-model="customValue"></v-switch>
              <v-text-field
                v-if="customValue"
                type="number"
                v-model="value_max"
                label="Maximum value"
              ></v-text-field>
              <v-text-field
                v-if="customValue"
                type="number"
                v-model="value_min"
                label="Minimum value"
              ></v-text-field>
            </v-card-text>
            <!-- Outside the scrolling area, so it's seen whatever the scroll position. -->
            <v-alert
              v-if="error"
              type="error"
              variant="tonal"
              density="compact"
              class="mx-4 mb-2"
              :text="error"
            />

            <v-divider></v-divider>

            <v-card-actions>
              <v-btn text="Close" @click="isActive.value = false"></v-btn>

              <v-spacer></v-spacer>

              <v-btn
                color="surface-variant"
                text="Save"
                variant="flat"
                type="submit"
                :loading="saving"
              ></v-btn>
            </v-card-actions>
          </v-card>
        </v-form>
      </template>
    </v-dialog>
  </div>
</template>
