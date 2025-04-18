import { get, post, put, del } from '@/utils/request'

export interface User {
  id: number
  username: string
  email: string
  created_at: string
  updated_at: string
}

export interface CreateUserParams {
  username: string
  email: string
  password: string
}

export interface UpdateUserParams {
  username?: string
  email?: string
  password?: string
}

// 获取用户列表
export const getUsers = () => {
  return get<User[]>('/users')
}

// 获取单个用户
export const getUser = (id: number) => {
  return get<User>(`/users/${id}`)
}

// 创建用户
export const createUser = (data: CreateUserParams) => {
  return post<User>('/users', data)
}

// 更新用户
export const updateUser = (id: number, data: UpdateUserParams) => {
  return put<User>(`/users/${id}`, data)
}

// 删除用户
export const deleteUser = (id: number) => {
  return del(`/users/${id}`)
} 