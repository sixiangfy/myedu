<template>
  <el-button 
    type="primary" 
    :loading="loading"
    :icon="DownloadIcon"
    @click="downloadTemplate"
  >
    {{ buttonText }}
  </el-button>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { Download as DownloadIcon } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useLoadingStore } from '@/store'

// 定义props
const props = defineProps({
  // API 接口地址
  url: {
    type: String,
    required: true
  },
  // 按钮文本
  buttonText: {
    type: String,
    default: '下载模板'
  },
  // 下载的文件名
  fileName: {
    type: String,
    default: '模板.xlsx'
  },
  // 请求参数
  params: {
    type: Object,
    default: () => ({})
  },
  // 请求头
  headers: {
    type: Object,
    default: () => ({})
  }
})

// 状态
const loading = ref(false)
const loadingStore = useLoadingStore()

// 下载模板
const downloadTemplate = async () => {
  loading.value = true
  loadingStore.startLoading('download-template')
  
  try {
    // 构建查询参数
    const queryParams = new URLSearchParams()
    Object.entries(props.params).forEach(([key, value]) => {
      queryParams.append(key, String(value))
    })
    
    // 构建URL
    const url = props.url + (queryParams.toString() ? `?${queryParams.toString()}` : '')
    
    // 发起请求
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...props.headers
      }
    })
    
    if (!response.ok) {
      throw new Error(`下载失败，状态码：${response.status}`)
    }
    
    // 获取blob
    const blob = await response.blob()
    
    // 创建下载链接
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = props.fileName
    link.click()
    
    // 释放URL对象
    window.URL.revokeObjectURL(downloadUrl)
    
    ElMessage.success('模板下载成功')
  } catch (error) {
    console.error('模板下载失败', error)
    ElMessage.error('模板下载失败')
  } finally {
    loading.value = false
    loadingStore.finishLoading('download-template')
  }
}
</script> 