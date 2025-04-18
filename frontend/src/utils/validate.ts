/**
 * 检查URL是否为外部链接
 * @param {string} path 路径
 * @returns {boolean}
 */
export function isExternal(path: string): boolean {
  return /^(https?:|mailto:|tel:)/.test(path)
}

/**
 * 验证用户名
 * @param {string} str 用户名
 * @returns {boolean}
 */
export function validUsername(str: string): boolean {
  return str.trim().length >= 3
}

/**
 * 验证URL
 * @param {string} url 链接
 * @returns {boolean}
 */
export function validURL(url: string): boolean {
  const reg = /^(https?|ftp):\/\/([a-zA-Z0-9.-]+(:[a-zA-Z0-9.&%$-]+)*@)*((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}|([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.(com|edu|gov|int|mil|net|org|biz|arpa|info|name|pro|aero|coop|museum|[a-zA-Z]{2}))(:[0-9]+)*(\/($|[a-zA-Z0-9.,?'\\+&%$#=~_-]+))*$/
  return reg.test(url)
}

/**
 * 验证邮箱
 * @param {string} email 邮箱
 * @returns {boolean}
 */
export function validEmail(email: string): boolean {
  const reg = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
  return reg.test(email.toLowerCase())
}

/**
 * 验证手机号
 * @param {string} phone 手机号
 * @returns {boolean}
 */
export function validPhone(phone: string): boolean {
  const reg = /^1[3-9]\d{9}$/
  return reg.test(phone)
}

/**
 * 验证密码
 * @param {string} password 密码
 * @returns {boolean}
 */
export function validPassword(password: string): boolean {
  // 密码至少包含6个字符
  return password.length >= 6
} 