import { App } from 'vue'
import permission from './permission'

// 注册全局指令
export default {
  install(app: App) {
    // 权限指令
    app.directive('permission', permission)
    
    // 可以在这里添加其他自定义指令
  }
} 