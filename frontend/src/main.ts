import { createApp } from 'vue'
import App from './App.vue'
import { initTheme } from './design/theme'
import { createAppRouter } from './router'
import './design/tokens.css'
import './style.css'

initTheme()
createApp(App).use(createAppRouter()).mount('#app')
