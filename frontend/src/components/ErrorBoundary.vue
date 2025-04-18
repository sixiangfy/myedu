<template>
  <div>
    <template v-if="hasError">
      <slot name="error" :error="error" :reset="reset">
        <div class="error-boundary">
          <div class="error-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <h2>页面出错了</h2>
          <p>{{ errorMessage }}</p>
          <el-button type="primary" @click="reset">重试</el-button>
        </div>
      </slot>
    </template>
    <template v-else>
      <slot />
    </template>
  </div>
</template>

<script lang="ts" setup>
import { ref, onErrorCaptured, provide } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 错误状态
const hasError = ref(false)
const error = ref<Error | null>(null)
const errorInfo = ref<any>(null)
const errorMessage = ref<string>('')

// 捕获子组件的错误
onErrorCaptured((err, instance, info) => {
  console.error('错误边界捕获到错误:', err)
  hasError.value = true
  error.value = err as Error
  errorInfo.value = info
  errorMessage.value = err ? err.message || '发生未知错误' : '发生未知错误'
  
  // 记录错误日志
  logError(err, instance, info)
  
  // 阻止错误继续传播
  return false
})

// 重置错误状态
const reset = () => {
  hasError.value = false
  error.value = null
  errorInfo.value = null
  errorMessage.value = ''
}

// 记录错误到日志系统
const logError = (err: unknown, vm: any, info: string) => {
  // 这里可以实现将错误信息发送到服务器的逻辑
  console.group('组件错误')
  console.error(err)
  console.error('组件实例:', vm)
  console.error('错误信息:', info)
  console.groupEnd()
  
  // 可以在这里发送错误信息到服务器
  // sendErrorToServer({ error: err, componentName: vm?.$options?.name, info })
}

// 提供错误处理方法给子组件
provide('reportError', (err: Error) => {
  hasError.value = true
  error.value = err
  errorMessage.value = err.message || '发生未知错误'
  
  // 记录错误日志
  logError(err, null, 'manually reported')
})

defineExpose({
  reset,
  hasError,
  error
})
</script>

<style lang="scss" scoped>
.error-boundary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  min-height: 300px;
  
  .error-icon {
    font-size: 48px;
    color: #f56c6c;
    margin-bottom: 20px;
  }
  
  h2 {
    margin-top: 0;
    margin-bottom: 16px;
    color: #303133;
  }
  
  p {
    margin-bottom: 24px;
    color: #606266;
    max-width: 500px;
    overflow-wrap: break-word;
  }
}
</style> 