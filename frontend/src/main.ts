import { createApp } from 'vue'
import App from './App.vue'
import { initTheme } from './design/theme'
import './design/tokens.css'
import './style.css'

initTheme()
createApp(App).mount('#app')
