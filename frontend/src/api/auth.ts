import request from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshTokenResponse {
  access_token: string
  token_type: string
}

// 登录接口
export const login = (data: LoginParams) => {
  return request.post<LoginResponse>('/auth/login', data)
}

// 刷新token接口
export const refreshToken = (refreshToken: string) => {
  return request.post<RefreshTokenResponse>('/auth/refresh', {
    refresh_token: refreshToken
  })
} 