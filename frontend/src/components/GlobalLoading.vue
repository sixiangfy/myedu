<template>
  <transition name="fade">
    <div class="global-loading-mask" v-if="loadingStore.isLoading">
      <el-icon class="is-loading" :size="48">
        <Loading />
      </el-icon>
      <div class="loading-text">{{ loadingText }}</div>
    </div>
  </transition>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useLoadingStore } from '@/store'

// 加载状态
const loadingStore = useLoadingStore()

// 加载文本
const loadingText = computed(() => {
  const requests = Array.from(loadingStore.loadingRequests)
  if (requests.length === 0) return '加载中...'
  
  // 根据请求ID返回不同的加载文本
  if (requests.some(id => id.startsWith('upload:'))) {
    return '正在上传文件...'
  }
  
  if (requests.some(id => id.startsWith('download:'))) {
    return '正在准备下载...'
  }
  
  if (requests.some(id => id.startsWith('auth:'))) {
    return '正在验证身份...'
  }
  
  return '加载中...'
})
</script>

<style lang="scss" scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.global-loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  
  .el-icon {
    font-size: 48px;
    color: var(--el-color-primary);
  }
  
  .loading-text {
    margin-top: 16px;
    color: var(--el-color-primary);
    font-size: 16px;
  }
}
</style> 