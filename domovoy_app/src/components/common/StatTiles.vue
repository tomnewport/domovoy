<script setup lang="ts">
import type { StatTile } from '@/utils/tiles'

// A grid of headline numbers, each with how it compares with before. The
// arrow shows better or worse (not just up or down), always with its text.
const { tiles } = defineProps<{ tiles: StatTile[] }>()
</script>
<template>
  <div class="tiles" :style="{ '--tile-count': tiles.length }">
    <v-card v-for="tile in tiles" :key="tile.label" class="pa-3" variant="tonal">
      <div class="d-flex align-center ga-1 text-body-2 text-medium-emphasis">
        <v-icon :icon="tile.icon" size="16" />
        <span>{{ tile.label }}</span>
      </div>
      <div class="text-h5 font-weight-bold mt-1">{{ tile.value }}</div>
      <div class="tile__delta text-caption" :class="`tile__delta--${tile.delta.tone}`">
        <v-icon
          v-if="tile.delta.tone !== 'flat'"
          :icon="tile.delta.tone === 'up' ? 'mdi-arrow-up' : 'mdi-arrow-down'"
          size="12"
        />
        {{ tile.delta.text }}
      </div>
    </v-card>
  </div>
</template>
<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
/* An odd tile out on a phone takes the whole row. */
.tiles > :last-child:nth-child(odd) {
  grid-column: span 2;
}
@media (min-width: 720px) {
  .tiles {
    grid-template-columns: repeat(var(--tile-count), minmax(0, 1fr));
  }
  .tiles > :last-child:nth-child(odd) {
    grid-column: auto;
  }
}
.tile__delta {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.tile__delta--up {
  color: rgb(var(--v-theme-success));
}
.tile__delta--down {
  color: rgb(var(--v-theme-warning));
}
</style>
