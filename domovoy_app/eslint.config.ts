import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

// ESLint flat config (ESLint 9+). Replaces .eslintrc.cjs with the same rule
// sets: vue3-essential, eslint:recommended + TypeScript, Prettier owns formatting.
export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,
  skipFormatting,

  {
    rules: {
      // Existing single-word component names (Login, Logout, Register); renaming is out of scope for CI.
      'vue/multi-word-component-names': 'off',
      // Vuetify's v-data-table uses dotted slot names such as `v-slot:item.name`.
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
    },
  },
)
