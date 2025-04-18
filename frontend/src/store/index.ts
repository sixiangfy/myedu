import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

// 创建pinia实例
const pinia = createPinia()

// 使用持久化插件
pinia.use(piniaPluginPersistedstate)

// 导出store
export { useAuthStore } from './auth'
export { useUserStore } from './user'
export { useScoreStore } from './score'
export { useLoadingStore } from './loading'

export default pinia 