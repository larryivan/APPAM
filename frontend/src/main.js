import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { installApiInterceptors } from './lib/api'

installApiInterceptors(router)

createApp(App).use(router).mount('#app')
