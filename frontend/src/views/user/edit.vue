<template>
  <div class="user-edit-container">
    <div class="header">
      <h2>编辑用户</h2>
      <el-button @click="$router.push('/user/list')">返回列表</el-button>
    </div>
    
    <el-card class="form-card" v-loading="loading">
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
            placeholder="留空表示不修改密码" 
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
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { UserRole, UpdateUserParams } from '@/types/api'
import { updateUser, getUser } from '@/api/user'
import { useUserStore } from '@/store'

// 路由和用户store
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 获取用户ID
const userId = ref(Number(route.params.id))

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)
const submitting = ref(false)

// 角色选项
const roleOptions = [
  { value: UserRole.ADMIN, label: '管理员' },
  { value: UserRole.HEADTEACHER, label: '班主任' },
  { value: UserRole.TEACHER, label: '教师' },
  { value: UserRole.STUDENT, label: '学生' }
]

// 表单数据
const formData = reactive<UpdateUserParams & { is_active: boolean }>({
  username: '',
  password: '',
  role: UserRole.STUDENT,
  email: '',
  phone: '',
  is_active: true
})

// 表单验证规则（密码可选）
const formRules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  email: [
    { required: false, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { required: false, message: '请输入电话', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
  ],
  password: [
    { required: false, trigger: 'blur' },
    { min: 6, message: '如果输入密码，不能少于 6 个字符', trigger: 'blur' }
  ]
})

// 获取用户信息
const fetchUserDetail = async () => {
  if (!userId.value) return
  
  try {
    loading.value = true
    const userData = await userStore.fetchUserDetail(userId.value)
    
    if (userData) {
      // 更新表单数据（不包含密码）
      formData.username = userData.username
      formData.role = userData.role
      formData.email = userData.email || ''
      formData.phone = userData.phone || ''
      formData.is_active = userData.is_active
      formData.password = '' // 密码字段置空
    } else {
      ElMessage.error('获取用户信息失败')
      router.push('/user/list')
    }
  } catch (error) {
    console.error('获取用户详情失败', error)
    ElMessage.error('获取用户详情失败')
    router.push('/user/list')
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value || !userId.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        submitting.value = true
        
        // 如果密码为空，则不修改密码
        const updateData: UpdateUserParams = { ...formData }
        if (!updateData.password) {
          delete updateData.password
        }
        
        await updateUser(userId.value, updateData)
        ElMessage.success('更新用户成功')
        router.push('/user/list')
      } catch (error: any) {
        console.error('更新用户失败', error)
        ElMessage.error(error.message || '更新用户失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  fetchUserDetail() // 重新获取用户数据
}

// 组件挂载时获取用户信息
onMounted(() => {
  fetchUserDetail()
})
</script>

<style lang="scss" scoped>
.user-edit-container {
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