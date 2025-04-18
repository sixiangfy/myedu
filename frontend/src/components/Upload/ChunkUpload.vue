<template>
  <div class="chunk-upload-container">
    <div class="upload-wrapper">
      <div
        class="upload-trigger"
        @click="handleClick"
        @drop.prevent="handleDrop"
        @dragover.prevent="handleDragOver"
        @dragleave.prevent="handleDragLeave"
        :class="{ 'is-drag-over': isDragOver }"
      >
        <!-- 上传图标 -->
        <div class="upload-icon">
          <slot name="icon">
            <el-icon><Upload /></el-icon>
          </slot>
        </div>
        
        <!-- 上传提示文字 -->
        <div class="upload-text">
          <slot name="text">
            <span>将文件拖到此处，或<em>点击上传</em></span>
          </slot>
        </div>
        
        <!-- 上传提示说明 -->
        <div class="upload-tip" v-if="tip">
          <slot name="tip">{{ tip }}</slot>
        </div>
      </div>
      
      <!-- 文件输入框 -->
      <input
        ref="inputRef"
        type="file"
        :accept="accept"
        :multiple="multiple"
        style="display: none"
        @change="handleFileChange"
      />
    </div>
    
    <!-- 上传列表 -->
    <div class="upload-list" v-if="fileList.length > 0">
      <div
        v-for="(file, index) in fileList"
        :key="index"
        class="upload-item"
        :class="{ 'is-uploading': file.status === 'uploading' }"
      >
        <!-- 文件名 -->
        <div class="file-name">
          <el-icon class="file-icon"><Document /></el-icon>
          <span>{{ file.name }}</span>
        </div>
        
        <!-- 进度条 -->
        <el-progress
          v-if="file.status === 'uploading'"
          :percentage="file.progress || 0"
          :stroke-width="4"
          class="file-progress"
        />
        
        <!-- 状态 -->
        <div class="file-status">
          <el-tag v-if="file.status === 'success'" type="success">上传成功</el-tag>
          <el-tag v-else-if="file.status === 'error'" type="danger">上传失败</el-tag>
          <template v-else-if="file.status === 'uploading'">
            {{ file.progress || 0 }}%
          </template>
        </div>
        
        <!-- 操作按钮 -->
        <div class="file-action">
          <el-button
            v-if="file.status === 'uploading'"
            @click="cancelUpload(file)"
            type="danger"
            size="small"
            circle
            :icon="Close"
          />
          <el-button
            v-else-if="file.status === 'error'"
            @click="retryUpload(file)"
            type="primary"
            size="small"
            circle
            :icon="RefreshRight"
          />
          <el-button
            v-else
            @click="removeFile(index)"
            type="danger"
            size="small"
            circle
            :icon="Delete"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue'
import { Document, Upload, Delete, Close, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useLoadingStore } from '@/store'

// 定义props
const props = defineProps({
  // 文件类型限制
  accept: {
    type: String,
    default: '*'
  },
  // 是否允许多选
  multiple: {
    type: Boolean,
    default: false
  },
  // 上传提示
  tip: {
    type: String,
    default: ''
  },
  // 接口地址
  action: {
    type: String,
    required: true
  },
  // 请求头
  headers: {
    type: Object,
    default: () => ({})
  },
  // 最大文件大小(MB)
  maxSize: {
    type: Number,
    default: 100
  },
  // 分片大小(MB)，默认5MB
  chunkSize: {
    type: Number,
    default: 5
  },
  // 同时上传的分片数
  simultaneousUploads: {
    type: Number,
    default: 3
  },
  // 是否自动上传
  autoUpload: {
    type: Boolean,
    default: true
  },
  // 额外参数
  data: {
    type: Object,
    default: () => ({})
  }
})

// 定义事件
const emit = defineEmits([
  'file-change',
  'upload-success',
  'upload-error',
  'upload-progress',
  'upload-complete'
])

// 引用
const inputRef = ref<HTMLInputElement | null>(null)
const loadingStore = useLoadingStore()

// 文件列表
const fileList = ref<any[]>([])
const isDragOver = ref(false)

// 当前活跃的请求
const activeRequests = ref<Record<string, XMLHttpRequest[]>>({})

// 触发文件选择
const handleClick = () => {
  inputRef.value?.click()
}

// 处理文件选择
const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  
  const files = Array.from(input.files)
  validateAndAddFiles(files)
  
  // 重置input值
  input.value = ''
}

// 处理拖拽
const handleDragOver = (e: DragEvent) => {
  isDragOver.value = true
  e.dataTransfer!.dropEffect = 'copy'
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  validateAndAddFiles(files)
}

// 验证并添加文件到列表
const validateAndAddFiles = (files: File[]) => {
  for (const file of files) {
    // 检查文件大小
    if (file.size > props.maxSize * 1024 * 1024) {
      ElMessage.error(`文件 ${file.name} 超过最大大小限制 ${props.maxSize}MB`)
      continue
    }
    
    // 添加到文件列表
    fileList.value.push({
      raw: file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'waiting',
      progress: 0,
      chunks: []
    })
  }
  
  // 触发文件改变事件
  emit('file-change', fileList.value)
  
  // 如果自动上传，则开始上传
  if (props.autoUpload && fileList.value.length > 0) {
    startUpload()
  }
}

// 开始上传所有文件
const startUpload = () => {
  fileList.value.forEach(file => {
    if (file.status === 'waiting' || file.status === 'error') {
      uploadFile(file)
    }
  })
}

// 上传单个文件
const uploadFile = (file: any) => {
  // 设置为上传中状态
  file.status = 'uploading'
  
  // 计算分片
  const chunkSize = props.chunkSize * 1024 * 1024
  const chunks = Math.ceil(file.size / chunkSize)
  
  // 初始化分片信息
  file.chunks = Array(chunks).fill(0).map((_, index) => ({
    index,
    start: index * chunkSize,
    end: Math.min((index + 1) * chunkSize, file.size),
    progress: 0,
    status: 'waiting'
  }))
  
  // 计算文件唯一标识
  file.identifier = calculateFileIdentifier(file.raw)
  
  // 初始化请求列表
  activeRequests.value[file.identifier] = []
  
  // 初始化上传器
  uploadChunks(file)
}

// 计算文件标识符
const calculateFileIdentifier = (file: File): string => {
  return `${file.name}_${file.size}_${file.lastModified}`
}

// 上传分片
const uploadChunks = async (file: any) => {
  // 先创建上传任务
  try {
    const createResponse = await createUploadTask(file)
    file.uploadId = createResponse.upload_id
    
    // 上传分片
    let runningUploads = 0
    const maxConcurrent = props.simultaneousUploads
    
    for (const chunk of file.chunks) {
      if (runningUploads >= maxConcurrent) {
        // 等待一个分片上传完成
        await new Promise(resolve => {
          const checkInterval = setInterval(() => {
            if (runningUploads < maxConcurrent) {
              clearInterval(checkInterval)
              resolve(true)
            }
          }, 100)
        })
      }
      
      if (chunk.status !== 'success') {
        runningUploads++
        uploadChunk(file, chunk).finally(() => {
          runningUploads--
        })
      }
    }
    
    // 等待所有分片上传完成
    await checkAllChunksUploaded(file)
    
  } catch (error) {
    console.error('上传失败', error)
    file.status = 'error'
    emit('upload-error', file, error)
  }
}

// 创建上传任务
const createUploadTask = async (file: any) => {
  const formData = new FormData()
  formData.append('filename', file.name)
  formData.append('size', file.size.toString())
  formData.append('mime_type', file.type)
  formData.append('chunk_size', (props.chunkSize * 1024 * 1024).toString())
  formData.append('chunks', file.chunks.length.toString())
  
  // 添加额外参数
  Object.entries(props.data).forEach(([key, value]) => {
    formData.append(key, String(value))
  })
  
  // 开始加载
  loadingStore.startLoading(`upload:create:${file.identifier}`)
  
  try {
    const response = await fetch(`${props.action}/create`, {
      method: 'POST',
      headers: {
        ...props.headers,
      },
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`创建上传任务失败，状态码：${response.status}`)
    }
    
    return await response.json()
  } finally {
    loadingStore.finishLoading(`upload:create:${file.identifier}`)
  }
}

// 上传单个分片
const uploadChunk = async (file: any, chunk: any) => {
  // 设置分片状态
  chunk.status = 'uploading'
  
  // 获取分片数据
  const chunkData = file.raw.slice(chunk.start, chunk.end)
  
  // 创建表单数据
  const formData = new FormData()
  formData.append('upload_id', file.uploadId)
  formData.append('chunk_index', chunk.index.toString())
  formData.append('file', chunkData, file.name)
  
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    
    // 保存请求对象
    activeRequests.value[file.identifier].push(xhr)
    
    // 进度事件
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        chunk.progress = Math.round((e.loaded / e.total) * 100)
        updateFileProgress(file)
      }
    }
    
    // 完成事件
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        chunk.status = 'success'
        chunk.progress = 100
        updateFileProgress(file)
        
        // 从活跃请求中移除
        const index = activeRequests.value[file.identifier].indexOf(xhr)
        if (index > -1) {
          activeRequests.value[file.identifier].splice(index, 1)
        }
        
        resolve()
      } else {
        chunk.status = 'error'
        updateFileProgress(file)
        
        // 从活跃请求中移除
        const index = activeRequests.value[file.identifier].indexOf(xhr)
        if (index > -1) {
          activeRequests.value[file.identifier].splice(index, 1)
        }
        
        reject(new Error(`分片上传失败，状态码：${xhr.status}`))
      }
    }
    
    // 错误事件
    xhr.onerror = () => {
      chunk.status = 'error'
      updateFileProgress(file)
      
      // 从活跃请求中移除
      const index = activeRequests.value[file.identifier].indexOf(xhr)
      if (index > -1) {
        activeRequests.value[file.identifier].splice(index, 1)
      }
      
      reject(new Error('网络错误，分片上传失败'))
    }
    
    // 开始请求
    xhr.open('POST', `${props.action}/chunk`, true)
    
    // 设置请求头
    Object.entries(props.headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, String(value))
    })
    
    xhr.send(formData)
  })
}

// 检查所有分片是否上传完成
const checkAllChunksUploaded = async (file: any) => {
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      const allUploaded = file.chunks.every(chunk => chunk.status === 'success')
      const hasError = file.chunks.some(chunk => chunk.status === 'error')
      
      if (allUploaded) {
        clearInterval(checkInterval)
        // 合并分片
        mergeChunks(file).then(resolve).catch(reject)
      } else if (hasError) {
        clearInterval(checkInterval)
        file.status = 'error'
        emit('upload-error', file, new Error('部分分片上传失败'))
        reject(new Error('部分分片上传失败'))
      }
    }, 500)
  })
}

// 合并分片
const mergeChunks = async (file: any) => {
  try {
    loadingStore.startLoading(`upload:merge:${file.identifier}`)
    
    const formData = new FormData()
    formData.append('upload_id', file.uploadId)
    formData.append('filename', file.name)
    formData.append('total_chunks', file.chunks.length.toString())
    
    // 添加额外参数
    Object.entries(props.data).forEach(([key, value]) => {
      formData.append(key, String(value))
    })
    
    const response = await fetch(`${props.action}/complete`, {
      method: 'POST',
      headers: {
        ...props.headers,
      },
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`合并分片失败，状态码：${response.status}`)
    }
    
    const result = await response.json()
    
    // 更新文件状态
    file.status = 'success'
    file.url = result.url
    file.progress = 100
    
    // 触发上传成功事件
    emit('upload-success', file, result)
    
    // 检查所有文件是否都已上传完成
    const allComplete = fileList.value.every(f => 
      f.status === 'success' || f.status === 'error'
    )
    
    if (allComplete) {
      emit('upload-complete', fileList.value)
    }
    
    return result
  } catch (error) {
    file.status = 'error'
    emit('upload-error', file, error)
    throw error
  } finally {
    loadingStore.finishLoading(`upload:merge:${file.identifier}`)
  }
}

// 更新文件进度
const updateFileProgress = (file: any) => {
  const totalProgress = file.chunks.reduce((sum, chunk) => sum + chunk.progress, 0)
  file.progress = Math.round(totalProgress / file.chunks.length)
  
  // 触发进度事件
  emit('upload-progress', file, file.progress)
}

// 取消上传
const cancelUpload = (file: any) => {
  if (file.status !== 'uploading') return
  
  // 取消所有活跃的请求
  if (activeRequests.value[file.identifier]) {
    activeRequests.value[file.identifier].forEach(xhr => xhr.abort())
    activeRequests.value[file.identifier] = []
  }
  
  // 更新文件状态
  file.status = 'error'
  file.progress = 0
}

// 重试上传
const retryUpload = (file: any) => {
  file.progress = 0
  file.chunks = file.chunks.map(chunk => ({
    ...chunk,
    progress: 0,
    status: 'waiting'
  }))
  
  uploadFile(file)
}

// 删除文件
const removeFile = (index: number) => {
  const file = fileList.value[index]
  
  // 如果正在上传，先取消上传
  if (file.status === 'uploading') {
    cancelUpload(file)
  }
  
  // 从列表中移除
  fileList.value.splice(index, 1)
}

// 公开方法
defineExpose({
  fileList,
  upload: startUpload,
  clearFiles: () => {
    fileList.value = []
  }
})
</script>

<style lang="scss" scoped>
.chunk-upload-container {
  .upload-wrapper {
    display: flex;
    flex-direction: column;
  }
  
  .upload-trigger {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 1px dashed #d9d9d9;
    border-radius: 6px;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s;
    padding: 30px 0;
    
    &:hover {
      border-color: #409EFF;
    }
    
    &.is-drag-over {
      border-color: #409EFF;
      background-color: rgba(64, 158, 255, 0.1);
    }
  }
  
  .upload-icon {
    font-size: 28px;
    color: #8c939d;
    margin-bottom: 10px;
  }
  
  .upload-text {
    font-size: 14px;
    color: #606266;
    margin-bottom: 10px;
    
    em {
      color: #409EFF;
      font-style: normal;
    }
  }
  
  .upload-tip {
    font-size: 12px;
    color: #909399;
  }
  
  .upload-list {
    margin-top: 15px;
  }
  
  .upload-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 4px;
    background-color: #f5f7fa;
    transition: background-color 0.3s;
    
    &.is-uploading {
      background-color: #e6f7ff;
    }
    
    .file-name {
      flex: 1;
      display: flex;
      align-items: center;
      
      .file-icon {
        margin-right: 8px;
        color: #909399;
      }
      
      span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
    
    .file-progress {
      flex: 2;
      margin: 0 15px;
    }
    
    .file-status {
      width: 80px;
      text-align: center;
    }
    
    .file-action {
      margin-left: 10px;
    }
  }
}
</style> 