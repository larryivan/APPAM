import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { installApiInterceptors } from './lib/api'
import Icon from './components/ui/Icon.vue'

installApiInterceptors(router)

const app = createApp(App)
app.component('Icon', Icon)
app.use(router).mount('#app')
