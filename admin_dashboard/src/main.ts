import './styles/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useUiStore } from './stores/ui'

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)
// Set day/night on <html> before the first paint.
useUiStore(pinia)
app.use(router)

app.mount('#app')
