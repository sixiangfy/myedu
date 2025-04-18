import { UserRole } from '@/types/api'

// 获取用户角色
export const getUserRole = (): UserRole => {
  const role = localStorage.getItem('user_role')
  return role as UserRole || UserRole.STUDENT
}

// 检查是否已登录
export const isLoggedIn = (): boolean => {
  return !!localStorage.getItem('access_token')
}

// 检查是否有权限
export const hasPermission = (roles: UserRole[]): boolean => {
  const userRole = getUserRole()
  return roles.includes(userRole)
}

// 权限等级映射（用于比较权限大小）
const permissionLevelMap = {
  [UserRole.ADMIN]: 4,
  [UserRole.HEADTEACHER]: 3,
  [UserRole.TEACHER]: 2,
  [UserRole.STUDENT]: 1
}

// 检查权限等级是否足够
export const hasPermissionLevel = (requiredRole: UserRole): boolean => {
  const userRole = getUserRole()
  return permissionLevelMap[userRole] >= permissionLevelMap[requiredRole]
}

// 清除认证信息
export const clearAuth = (): void => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_role')
  localStorage.removeItem('user_info')
} 