import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  // 保存所有正在加载中的请求标识
  const loadingRequests = ref<Set<string>>(new Set())
  
  // 计算全局加载状态
  const isLoading = computed(() => loadingRequests.value.size > 0)
  
  // 设置加载状态
  const startLoading = (requestId: string) => {
    loadingRequests.value.add(requestId)
  }
  
  // 结束加载状态
  const finishLoading = (requestId: string) => {
    loadingRequests.value.delete(requestId)
  }
  
  // 清除所有加载状态
  const clearAllLoadings = () => {
    loadingRequests.value.clear()
  }
  
  // 获取特定模块加载状态
  const getModuleLoading = (module: string) => {
    return Array.from(loadingRequests.value).some(id => id.startsWith(`${module}:`))
  }
  
  return {
    loadingRequests,
    isLoading,
    startLoading,
    finishLoading,
    clearAllLoadings,
    getModuleLoading
  }
}) 