<template>
  <error-boundary>
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
    <global-loading />
  </error-boundary>
</template>

<script lang="ts" setup>
import { onMounted, onBeforeUnmount } from 'vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import GlobalLoading from '@/components/GlobalLoading.vue'
import { useLoadingStore } from '@/store'

// 获取loading store
const loadingStore = useLoadingStore()

// 处理全局错误
const handleGlobalError = (event: ErrorEvent) => {
  console.error('捕获到全局错误:', event.error)
  // 这里可以添加错误上报逻辑
  event.preventDefault()
}

// 处理未捕获的Promise错误
const handlePromiseRejection = (event: PromiseRejectionEvent) => {
  console.error('捕获到未处理的Promise拒绝:', event.reason)
  // 这里可以添加错误上报逻辑
  event.preventDefault()
}

// 页面加载时添加全局错误处理
onMounted(() => {
  window.addEventListener('error', handleGlobalError)
  window.addEventListener('unhandledrejection', handlePromiseRejection)
})

// 组件卸载前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('error', handleGlobalError)
  window.removeEventListener('unhandledrejection', handlePromiseRejection)
  // 清除所有加载状态
  loadingStore.clearAllLoadings()
})
</script>

<style lang="scss">
@import '@/styles/main.scss';

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--el-text-color-primary);
}
</style> 