import { DirectiveBinding } from 'vue'
import { UserRole } from '@/types/api'
import { hasPermission, hasPermissionLevel } from '@/utils/permission'

// 权限指令类型
type PermissionValue = 
  | UserRole 
  | UserRole[] 
  | { 
      role?: UserRole | UserRole[],
      feature?: string,
      action?: string,
      resource?: string,
      condition?: (el: HTMLElement) => boolean
    }

export default {
  mounted(el: HTMLElement, binding: DirectiveBinding<PermissionValue>) {
    const { value } = binding
    
    if (!value) return
    
    // 简单角色数组模式: v-permission="[UserRole.ADMIN, UserRole.TEACHER]"
    if (Array.isArray(value)) {
      if (!hasPermission(value)) {
        el.parentNode?.removeChild(el)
      }
      return
    }
    
    // 简单角色级别模式: v-permission="UserRole.ADMIN"
    if (typeof value === 'string') {
      if (!hasPermissionLevel(value as UserRole)) {
        el.parentNode?.removeChild(el)
      }
      return
    }
    
    // 高级对象模式: v-permission="{ role: UserRole.ADMIN, feature: 'user', action: 'create' }"
    if (typeof value === 'object') {
      let hasAccess = true
      
      // 检查角色权限
      if (value.role) {
        if (Array.isArray(value.role)) {
          if (!hasPermission(value.role)) {
            hasAccess = false
          }
        } else {
          if (!hasPermissionLevel(value.role)) {
            hasAccess = false
          }
        }
      }
      
      // 检查功能权限 (feature+action组合)
      if (hasAccess && value.feature && value.action) {
        // 获取用户的功能权限列表 (假设存储在localStorage中)
        const featurePermissions = JSON.parse(localStorage.getItem('feature_permissions') || '{}')
        const key = `${value.feature}:${value.action}`
        
        if (!featurePermissions[key]) {
          hasAccess = false
        }
      }
      
      // 检查资源访问权限
      if (hasAccess && value.resource) {
        // 基于资源类型的权限检查，可以从localStorage获取或调用API
        const resourcePermissions = JSON.parse(localStorage.getItem('resource_permissions') || '{}')
        
        if (!resourcePermissions[value.resource]) {
          hasAccess = false
        }
      }
      
      // 自定义条件检查
      if (hasAccess && value.condition && typeof value.condition === 'function') {
        hasAccess = value.condition(el)
      }
      
      if (!hasAccess) {
        el.parentNode?.removeChild(el)
      }
    }
  }
} 