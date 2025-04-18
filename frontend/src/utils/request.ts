import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore, useLoadingStore } from '@/store'
import { generateUUID } from '@/utils/common'

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 是否正在刷新token
let isRefreshing = false
// 存储等待中的请求
let requests: Array<(token: string) => void> = []

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 生成请求ID
    const requestId = generateUUID()
    config.requestId = requestId
    
    // 设置加载状态
    if (config.showLoading !== false) {
      const loadingStore = useLoadingStore()
      const loadingKey = config.loadingKey || `request:${requestId}`
      loadingStore.startLoading(loadingKey)
      config.loadingKey = loadingKey
    }
    
    // 获取token
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }

    // 根据请求类型设置Content-Type
    if (config.data instanceof FormData) {
      config.headers['Content-Type'] = 'multipart/form-data'
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    // 移除加载状态
    if (response.config.showLoading !== false && response.config.loadingKey) {
      const loadingStore = useLoadingStore()
      loadingStore.finishLoading(response.config.loadingKey as string)
    }
    
    // 如果返回的是blob等数据，直接返回
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response.data
    }
    
    // 正常返回数据
    return response.data
  },
  async (error) => {
    const { response, config } = error
    
    // 移除加载状态
    if (config?.showLoading !== false && config?.loadingKey) {
      const loadingStore = useLoadingStore()
      loadingStore.finishLoading(config.loadingKey as string)
    }

    // 处理401错误
    if (response?.status === 401) {
      // 避免多个请求同时刷新token
      if (!isRefreshing) {
        isRefreshing = true
        
        try {
          // 调用刷新token接口
          const authStore = useAuthStore()
          const refreshSuccess = await authStore.refreshAuth()
          
          if (refreshSuccess) {
            // 刷新成功，更新token并重新请求
            config.headers.Authorization = `Bearer ${authStore.accessToken}`
            
            // 执行队列中的请求
            requests.forEach(cb => cb(authStore.accessToken))
            requests = []
            
            // 重试当前请求
            return service(config)
          } else {
            // 刷新失败，需要重新登录
            authStore.logout()
            ElMessage.error('登录已过期，请重新登录')
            return Promise.reject(new Error('登录已过期'))
          }
        } catch (err) {
          // 刷新token出错
          const authStore = useAuthStore()
          authStore.logout()
          ElMessage.error('登录已过期，请重新登录')
          return Promise.reject(new Error('刷新token失败'))
        } finally {
          isRefreshing = false
        }
      } else {
        // 正在刷新token，将请求加入队列
        return new Promise(resolve => {
          requests.push((token: string) => {
            config.headers.Authorization = `Bearer ${token}`
            resolve(service(config))
          })
        })
      }
    }

    // 处理其他错误
    if (response?.status === 400) {
      ElMessage.error('请求参数错误')
    } else if (response?.status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (response?.status === 404) {
      ElMessage.error('请求的资源不存在')
    } else if (response?.status === 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else {
      ElMessage.error(error.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

// 扩展AxiosRequestConfig类型
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    requestId?: string;
    loadingKey?: string;
    showLoading?: boolean;
  }
}

// 封装请求方法
export const get = <T = any>(url: string, params?: any, config?: AxiosRequestConfig) => {
  return service.get<T, T>(url, { params, ...config })
}

export const post = <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => {
  return service.post<T, T>(url, data, config)
}

export const put = <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => {
  return service.put<T, T>(url, data, config)
}

export const del = <T = any>(url: string, config?: AxiosRequestConfig) => {
  return service.delete<T, T>(url, config)
}

export default service 