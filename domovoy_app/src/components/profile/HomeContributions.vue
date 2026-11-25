<script setup lang="ts">
import { computed } from 'vue'
import type { components } from '@/services/domovoy/schema.d.ts'
import type { HomeStatistics } from '@/services/domovoy/stats'
import { memberColors } from '@/utils/memberColors'
import type { Period } from '@/utils/progress'

type Home = components['schemas']['HomeSchema']

// Your part of each home's points this period. How the home as a whole is
// doing lives on the home's own page, linked from here.
const { entries, period, userId } = defineProps<{
  entries: { home: Home; stats: HomeStatistics }[]
  period: Period
  userId: number
}>()

const periodLabel = computed(() => (period === 7 ? 'this week' : 'in the last 30 days'))
const sum = (values: number[]) => values.reduce((a, b) => a + b, 0)

const rows = computed(() =>
  entries.map(({ home, stats }) => {
    const total = sum(stats.users.map((u) => sum(u.daily_scores.slice(-period))))
    const mine = sum(stats.users.find((u) => u.id === userId)?.daily_scores.slice(-period) ?? [])
    return {
      id: home.id as number,
      name: home.name,
      mine,
      total,
      share: total ? mine / total : null,
      members: home.memberships.length,
      color: memberColors(home.memberships.map((m) => m.user.id)).get(userId) ?? '#9c9c9c'
    }
  })
)
</script>
<template>
  <v-card class="pa-4" variant="tonal">
    <div class="text-body-2 text-medium-emphasis mb-3">Your share {{ periodLabel }}</div>
    <div v-for="row in rows" :key="row.id" class="contribution">
      <div class="d-flex align-center justify-space-between">
        <span class="text-subtitle-1">{{ row.name }}</span>
        <v-btn
          :to="`/homes/${row.id}`"
          variant="text"
          size="small"
          append-icon="mdi-chevron-right"
          :aria-label="`${row.name}: home stats`"
        >
          Home stats
        </v-btn>
      </div>
      <template v-if="row.share !== null">
        <div class="d-flex align-baseline ga-2">
          <span class="text-h5 font-weight-bold">{{ Math.round(row.share * 100) }}%</span>
          <span class="text-body-2 text-medium-emphasis">
            {{ row.mine }} of {{ row.total }} points
            <template v-if="row.members > 1">
              · an even share would be {{ Math.round(100 / row.members) }}%
            </template>
          </span>
        </div>
        <div class="share mt-1" aria-hidden="true">
          <span
            class="share__fill"
            :style="{ width: `${row.share * 100}%`, background: row.color }"
          ></span>
          <span
            v-if="row.members > 1"
            class="share__even"
            :style="{ left: `${100 / row.members}%` }"
          ></span>
        </div>
      </template>
      <div v-else class="text-body-2 text-medium-emphasis">
        Nobody's earned points here {{ periodLabel }} yet.
      </div>
    </div>
  </v-card>
</template>
<style scoped>
.contribution + .contribution {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.share {
  position: relative;
  height: 8px;
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.share__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
}
.share__even {
  position: absolute;
  top: -3px;
  bottom: -3px;
  width: 2px;
  margin-left: -1px;
  background: rgba(var(--v-theme-on-surface), 0.6);
}
</style>
