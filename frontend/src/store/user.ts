import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { User, PageParams } from '@/types/api'
import { useAuthStore } from './auth'
import { getUsers, getUser } from '@/api/user'
import { ElMessage } from 'element-plus'

export const useUserStore = defineStore('user', () => {
  // 状态
  const userList = ref<User[]>([])
  const currentUser = ref<User | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(10)

  // 计算属性
  // 获取已过滤的用户列表（基于权限）
  const filteredUserList = computed(() => {
    const authStore = useAuthStore()
    // 管理员可以看到所有用户
    if (authStore.hasAdminAccess) {
      return userList.value
    }
    // 教师只能看到学生用户
    if (authStore.hasTeacherAccess) {
      return userList.value.filter(user => user.role === 'student')
    }
    // 学生只能看到自己的信息
    return userList.value.filter(user => user.username === authStore.username)
  })

  // 方法
  // 获取用户列表
  const fetchUsers = async (params?: PageParams) => {
    try {
      loading.value = true
      const pageParams = {
        page: params?.page || currentPage.value,
        page_size: params?.page_size || pageSize.value
      }
      
      const response = await getUsers(pageParams)
      userList.value = response.data || []
      total.value = response.total || 0
      
      if (params?.page) {
        currentPage.value = params.page
      }
      if (params?.page_size) {
        pageSize.value = params.page_size
      }
      
      return userList.value
    } catch (error: any) {
      ElMessage.error(error.message || '获取用户列表失败')
      return []
    } finally {
      loading.value = false
    }
  }

  // 获取用户详情
  const fetchUserDetail = async (id: number) => {
    const authStore = useAuthStore()
    
    // 检查权限
    if (!authStore.hasTeacherAccess && authStore.username !== id.toString()) {
      ElMessage.error('您没有权限查看其他用户的详细信息')
      return null
    }
    
    try {
      loading.value = true
      const response = await getUser(id)
      currentUser.value = response
      return currentUser.value
    } catch (error: any) {
      ElMessage.error(error.message || '获取用户详情失败')
      return null
    } finally {
      loading.value = false
    }
  }

  // 清除数据
  const clearUserData = () => {
    userList.value = []
    currentUser.value = null
    total.value = 0
    currentPage.value = 1
  }

  return {
    // 状态
    userList,
    currentUser,
    total,
    loading,
    currentPage,
    pageSize,
    
    // 计算属性
    filteredUserList,
    
    // 方法
    fetchUsers,
    fetchUserDetail,
    clearUserData
  }
}) 