import './assets/main.css'
import '@mdi/font/css/materialdesignicons.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DUserDisplay from '@/components/common/UserDisplay.vue'
import DDateDisplay from '@/components/common/DateDisplay.vue'
import DHomeDisplay from '@/components/common/HomeDisplay.vue'
import DEditableItem from '@/components/common/EditableItem.vue'

const lightTheme = {
  dark: false,
  colors: {
    primary: 'rgb(155, 35, 255)',
    secondary: 'rgb(0, 173, 226)'
  }
}

const darkTheme = {
  dark: true,
  colors: {
    primary: 'rgb(202, 138, 255)',
    secondary: 'rgb(24, 130, 163)',
    background: 'rgb(0, 39, 58)',
    surface: 'rgb(0, 59, 78)'
  }
}

const vuetify = createVuetify({
  components: { ...components, DUserDisplay, DDateDisplay, DHomeDisplay, DEditableItem },
  directives,

  theme: {
    defaultTheme: 'dark',
    themes: {
      light: lightTheme,
      dark: darkTheme
    }
  }
})

const app = createApp(App)
app.use(vuetify)
app.use(createPinia())
app.use(router)

app.mount('#app')
