/**
 * 生成UUID
 * @returns UUID字符串
 */
export const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * 格式化日期
 * @param date 日期对象或日期字符串
 * @param format 格式化模板，默认 YYYY-MM-DD HH:mm:ss
 * @returns 格式化后的日期字符串
 */
export const formatDate = (date: Date | string, format = 'YYYY-MM-DD HH:mm:ss'): string => {
  const d = date instanceof Date ? date : new Date(date)
  
  if (isNaN(d.getTime())) {
    return '无效日期'
  }
  
  const replacements = {
    'YYYY': d.getFullYear().toString(),
    'MM': (d.getMonth() + 1).toString().padStart(2, '0'),
    'DD': d.getDate().toString().padStart(2, '0'),
    'HH': d.getHours().toString().padStart(2, '0'),
    'mm': d.getMinutes().toString().padStart(2, '0'),
    'ss': d.getSeconds().toString().padStart(2, '0')
  }
  
  let result = format
  for (const [key, value] of Object.entries(replacements)) {
    result = result.replace(key, value)
  }
  
  return result
}

/**
 * 防抖函数
 * @param fn 需要防抖的函数
 * @param delay 延迟时间（毫秒）
 * @returns 防抖后的函数
 */
export const debounce = <T extends (...args: any[]) => any>(fn: T, delay = 300): ((...args: Parameters<T>) => void) => {
  let timer: ReturnType<typeof setTimeout> | null = null
  
  return function(this: any, ...args: Parameters<T>) {
    if (timer) {
      clearTimeout(timer)
    }
    
    timer = setTimeout(() => {
      fn.apply(this, args)
      timer = null
    }, delay)
  }
}

/**
 * 节流函数
 * @param fn 需要节流的函数
 * @param delay 延迟时间（毫秒）
 * @returns 节流后的函数
 */
export const throttle = <T extends (...args: any[]) => any>(fn: T, delay = 300): ((...args: Parameters<T>) => void) => {
  let lastTime = 0
  
  return function(this: any, ...args: Parameters<T>) {
    const now = Date.now()
    
    if (now - lastTime >= delay) {
      fn.apply(this, args)
      lastTime = now
    }
  }
}

/**
 * 将数字或字符串转换为带货币符号的金额
 * @param value 数字或字符串
 * @param currency 货币符号，默认为 ￥
 * @param decimals 小数位数，默认为 2
 * @returns 带货币符号的金额字符串
 */
export const formatCurrency = (value: number | string, currency = '￥', decimals = 2): string => {
  const number = parseFloat(value.toString())
  
  if (isNaN(number)) {
    return ''
  }
  
  return currency + number.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 深拷贝对象
 * @param obj 需要深拷贝的对象
 * @returns 深拷贝后的对象
 */
export const deepClone = <T>(obj: T): T => {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  
  if (obj instanceof Object) {
    const copy = {} as Record<string, any>
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        copy[key] = deepClone((obj as Record<string, any>)[key])
      }
    }
    return copy as T
  }
  
  return obj
}

/**
 * 获取文件扩展名
 * @param filename 文件名
 * @returns 扩展名（不包含点号）
 */
export const getFileExtension = (filename: string): string => {
  return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2)
}

/**
 * 文件大小格式化
 * @param bytes 字节大小
 * @param decimals 小数位数，默认为 2
 * @returns 格式化后的文件大小字符串
 */
export const formatFileSize = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
} 