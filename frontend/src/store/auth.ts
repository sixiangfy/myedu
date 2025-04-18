import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { UserRole } from '@/types/api'
import { login, refreshToken } from '@/api/auth'
import router from '@/router'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const accessToken = ref<string>('')
  const refreshTokenValue = ref<string>('')
  const userRole = ref<UserRole>(UserRole.STUDENT)
  const username = ref<string>('')
  const isLoggedIn = ref<boolean>(false)

  // 计算属性
  const hasAdminAccess = computed(() => userRole.value === UserRole.ADMIN)
  const hasTeacherAccess = computed(() => 
    [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER].includes(userRole.value)
  )
  const roleName = computed(() => {
    const roleMap = {
      [UserRole.ADMIN]: '管理员',
      [UserRole.HEADTEACHER]: '班主任',
      [UserRole.TEACHER]: '教师',
      [UserRole.STUDENT]: '学生'
    }
    return roleMap[userRole.value] || '用户'
  })

  // 方法
  // 用户登录
  const loginUser = async (loginData: { username: string, password: string }) => {
    try {
      const response = await login(loginData)
      
      // 存储token
      accessToken.value = response.access_token
      refreshTokenValue.value = response.refresh_token
      
      // 根据用户名判断角色（实际项目中应该从后端获取）
      if (loginData.username.includes('admin')) {
        userRole.value = UserRole.ADMIN
      } else if (loginData.username.includes('headteacher')) {
        userRole.value = UserRole.HEADTEACHER
      } else if (loginData.username.includes('teacher')) {
        userRole.value = UserRole.TEACHER
      } else {
        userRole.value = UserRole.STUDENT
      }
      
      username.value = loginData.username
      isLoggedIn.value = true
      
      return true
    } catch (error: any) {
      ElMessage.error(error.message || '登录失败')
      return false
    }
  }

  // 刷新token
  const refreshAuth = async () => {
    if (!refreshTokenValue.value) {
      return false
    }
    
    try {
      const response = await refreshToken(refreshTokenValue.value)
      accessToken.value = response.access_token
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  // 登出
  const logout = () => {
    accessToken.value = ''
    refreshTokenValue.value = ''
    userRole.value = UserRole.STUDENT
    username.value = ''
    isLoggedIn.value = false
    
    router.push('/login')
  }

  // 检查是否有权限
  const hasPermission = (roles: UserRole[]) => {
    return roles.includes(userRole.value)
  }

  // 检查权限等级是否足够
  const hasPermissionLevel = (requiredRole: UserRole) => {
    const permissionLevelMap = {
      [UserRole.ADMIN]: 4,
      [UserRole.HEADTEACHER]: 3,
      [UserRole.TEACHER]: 2,
      [UserRole.STUDENT]: 1
    }
    
    return permissionLevelMap[userRole.value] >= permissionLevelMap[requiredRole]
  }

  return {
    // 状态
    accessToken,
    refreshTokenValue,
    userRole,
    username,
    isLoggedIn,
    
    // 计算属性
    hasAdminAccess,
    hasTeacherAccess,
    roleName,
    
    // 方法
    loginUser,
    refreshAuth,
    logout,
    hasPermission,
    hasPermissionLevel
  }
}, {
  // 持久化配置
  persist: {
    key: 'auth-store',
    storage: localStorage,
    paths: ['accessToken', 'refreshTokenValue', 'userRole', 'username', 'isLoggedIn']
  }
}) 