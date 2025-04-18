<template>
  <div class="user-create-container">
    <div class="header">
      <h2>创建用户</h2>
      <el-button @click="$router.push('/user/list')">返回列表</el-button>
    </div>
    
    <el-card class="form-card">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        status-icon
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="formData.password" 
            placeholder="请输入密码" 
            type="password" 
            show-password
          />
        </el-form-item>
        
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色">
            <el-option
              v-for="item in roleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        
        <el-form-item label="电话" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入电话" />
        </el-form-item>
        
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">创建</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { UserRole, CreateUserParams } from '@/types/api'
import { createUser } from '@/api/user'

// 路由
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)

// 角色选项
const roleOptions = [
  { value: UserRole.ADMIN, label: '管理员' },
  { value: UserRole.HEADTEACHER, label: '班主任' },
  { value: UserRole.TEACHER, label: '教师' },
  { value: UserRole.STUDENT, label: '学生' }
]

// 表单数据
const formData = reactive<CreateUserParams & { is_active: boolean }>({
  username: '',
  password: '',
  role: UserRole.STUDENT,
  email: '',
  phone: '',
  is_active: true
})

// 表单验证规则
const formRules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码不能少于 6 个字符', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  email: [
    { required: false, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { required: false, message: '请输入电话', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ]
})

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true
        await createUser(formData)
        ElMessage.success('创建用户成功')
        router.push('/user/list')
      } catch (error: any) {
        console.error('创建用户失败', error)
        ElMessage.error(error.message || '创建用户失败')
      } finally {
        loading.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}
</script>

<style lang="scss" scoped>
.user-create-container {
  padding: 20px;
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
    }
  }
  
  .form-card {
    max-width: 800px;
  }
}
</style> 