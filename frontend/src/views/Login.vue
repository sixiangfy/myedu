<template>
  <div class="login-container">
    <el-form
      ref="loginFormRef"
      :model="loginForm"
      :rules="loginRules"
      class="login-form"
      autocomplete="on"
      label-position="left"
    >
      <div class="title-container">
        <h3 class="title">教育管理系统</h3>
      </div>

      <el-form-item prop="username">
        <el-input
          v-model="loginForm.username"
          placeholder="用户名"
          name="username"
          type="text"
          autocomplete="on"
          prefix-icon="User"
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          placeholder="密码"
          name="password"
          :type="passwordType"
          autocomplete="on"
          prefix-icon="Lock"
          @keyup.enter="handleLogin"
        />
        <span class="show-pwd" @click="showPwd">
          <el-icon>
            <component :is="passwordType === 'password' ? 'View' : 'Hide'" />
          </el-icon>
        </span>
      </el-form-item>

      <el-button
        :loading="loading"
        type="primary"
        style="width: 100%; margin-bottom: 30px"
        @click.prevent="handleLogin"
      >
        登录
      </el-button>
    </el-form>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { User, Lock, View, Hide } from '@element-plus/icons-vue'
import { generateRoutes } from '@/router'
import { useAuthStore } from '@/store'

// 路由
const router = useRouter()
const route = useRoute()

// 获取authStore
const authStore = useAuthStore()

// 表单引用
const loginFormRef = ref<FormInstance>()

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const loginRules = reactive<FormRules>({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
})

// 密码类型和加载状态
const passwordType = ref('password')
const loading = ref(false)

// 显示密码
const showPwd = () => {
  passwordType.value = passwordType.value === 'password' ? '' : 'password'
}

// 登录处理
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true
        
        // 使用authStore登录
        const success = await authStore.loginUser({
          username: loginForm.username,
          password: loginForm.password
        })
        
        if (success) {
          // 动态生成路由
          generateRoutes()
          
          // 跳转到首页或重定向页面
          const redirect = route.query.redirect as string
          router.push(redirect || '/')
          
          ElMessage.success('登录成功')
        }
      } catch (error: any) {
        ElMessage.error(error.message || '登录失败，请检查用户名和密码')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  width: 100%;
  background-color: #2d3a4b;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-form {
  width: 520px;
  max-width: 100%;
  padding: 35px 35px 15px;
  background: #fff;
  border-radius: 10px;
}

.title-container {
  position: relative;
  .title {
    margin: 0 auto 40px;
    text-align: center;
    font-weight: bold;
    color: #2d3a4b;
  }
}

.show-pwd {
  position: absolute;
  right: 10px;
  top: 6px;
  cursor: pointer;
}
</style> 