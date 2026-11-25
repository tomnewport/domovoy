<script setup lang="ts">
import { computed } from 'vue'
import type { components } from '@/services/domovoy/schema.d.ts'
import EditableItem from '@/components/common/EditableItem.vue'
import { client, getHeaders } from '@/services/domovoy'
import { apiErrorMessage } from '@/services/domovoy/errors'
import { useHomesStore } from '@/stores/homes'
import { useRegularJobStore } from '@/stores/regular-job'
import { memberColors, textOn } from '@/utils/memberColors'

type Home = components['schemas']['HomeSchema']

// A home's name and description, who's in it, and the way to its jobs.
const { home, currentUserId } = defineProps<{ home: Home; currentUserId: number | null }>()
const homesStore = useHomesStore()
const regularJobStore = useRegularJobStore()

async function update(body: { name?: string; description?: string }) {
  const { response, error } = await client.PATCH('/api/homes/v1/homes/{home_id}', {
    params: { path: { home_id: String(home.id) } },
    body,
    headers: getHeaders()
  })
  if (!response.ok) throw new Error(apiErrorMessage(error, 'Could not save the change'))
  await homesStore.reloadHomes()
}
const setName = (name: string) => update({ name })
const setDescription = (description: string) => update({ description })

const colors = computed(() => memberColors(home.memberships.map((m) => m.user.id)))
const members = computed(() =>
  [...home.memberships]
    .map((m) => m.user)
    .sort((a, b) => a.id - b.id)
    .map((user) => ({
      id: user.id,
      name: user.name_full,
      short: user.name_short ?? user.name_full,
      color: colors.value.get(user.id) ?? '#9c9c9c',
      isSelf: user.id === currentUserId
    }))
)
const jobCount = computed(
  () => regularJobStore.definitions.filter((d) => d.home === home.id).length
)

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
</script>
<template>
  <div>
    <EditableItem label="Name" :value="home.name" :onChange="setName" />
    <EditableItem label="Description" :value="home.description || ''" :onChange="setDescription" />

    <div class="text-subtitle-1 mt-4">Jobs</div>
    <div class="d-flex align-center justify-space-between">
      <span class="text-body-2 text-medium-emphasis">
        <template v-if="regularJobStore.hasData">
          {{ jobCount }} {{ jobCount === 1 ? 'job' : 'jobs' }}
        </template>
      </span>
      <v-btn :to="`/homes/${home.id}/jobs`" variant="tonal" prepend-icon="mdi-pencil">
        Edit jobs
      </v-btn>
    </div>

    <div class="text-subtitle-1 mt-6">Members</div>
    <v-list bg-color="transparent" class="pa-0">
      <v-list-item v-for="member in members" :key="member.id" class="px-1">
        <template #prepend>
          <v-avatar
            size="36"
            :style="{ background: member.color, color: textOn(member.color) }"
            class="text-caption font-weight-bold"
          >
            {{ initials(member.name) }}
          </v-avatar>
        </template>
        <v-list-item-title>
          {{ member.name }}<template v-if="member.isSelf"> (you)</template>
        </v-list-item-title>
        <v-list-item-subtitle v-if="member.short !== member.name">
          {{ member.short }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </div>
</template>
