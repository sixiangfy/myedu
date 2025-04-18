import { createApp } from 'vue'
// import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import pinia from './store'
import directives from './directives'

// Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 全局组件
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import GlobalLoading from '@/components/GlobalLoading.vue'

// 样式
import './styles/main.scss'

const app = createApp(App)

// 注册Element Plus
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default'
})

// 注册全局组件
app.component('ErrorBoundary', ErrorBoundary)
app.component('GlobalLoading', GlobalLoading)

// 注册自定义指令
app.use(directives)

// app.use(createPinia())
app.use(pinia)
app.use(router)

app.mount('#app') 