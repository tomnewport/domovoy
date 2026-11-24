/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  root: true,
  'extends': [
    'plugin:vue/vue3-essential',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting'
  ],
  parserOptions: {
    ecmaVersion: 'latest'
  },
  rules: {
    // Existing single-word component names (Login, Logout, Register); renaming is out of scope for CI.
    'vue/multi-word-component-names': 'off',
    // Vuetify's v-data-table uses dotted slot names such as `v-slot:item.name`.
    'vue/valid-v-slot': ['error', { allowModifiers: true }]
  }
}
