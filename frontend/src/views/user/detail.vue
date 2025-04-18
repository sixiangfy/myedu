<template>
  <div class="user-detail-container">
    <div class="header">
      <h2>用户详情</h2>
      <div class="actions">
        <el-button type="primary" @click="$router.push(`/user/edit/${userId}`)">编辑</el-button>
        <el-button @click="$router.push('/user/list')">返回列表</el-button>
      </div>
    </div>

    <el-card class="detail-card" v-loading="loading">
      <template v-if="user">
        <el-descriptions border :column="1" size="large">
          <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ roleLabel }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ user.email || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ user.phone || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="user.is_active ? 'success' : 'danger'">
              {{ user.is_active ? '激活' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(user.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最后登录">{{ user.last_login ? formatDate(user.last_login) : '从未登录' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 学生特有信息 -->
        <template v-if="user.role === 'STUDENT' && user.student_info">
          <h3 class="section-title">学生信息</h3>
          <el-descriptions border :column="1" size="large">
            <el-descriptions-item label="学号">{{ user.student_info.student_id }}</el-descriptions-item>
            <el-descriptions-item label="班级">{{ user.student_info.class_name }}</el-descriptions-item>
            <el-descriptions-item label="入学年份">{{ user.student_info.enrollment_year }}</el-descriptions-item>
          </el-descriptions>
        </template>

        <!-- 教师特有信息 -->
        <template v-if="['TEACHER', 'HEADTEACHER'].includes(user.role) && user.teacher_info">
          <h3 class="section-title">教师信息</h3>
          <el-descriptions border :column="1" size="large">
            <el-descriptions-item label="工号">{{ user.teacher_info.teacher_id }}</el-descriptions-item>
            <el-descriptions-item label="科目">{{ user.teacher_info.subject }}</el-descriptions-item>
            <el-descriptions-item label="职称">{{ user.teacher_info.title }}</el-descriptions-item>
            <el-descriptions-item label="管理班级" v-if="user.role === 'HEADTEACHER'">
              {{ user.teacher_info.managed_class || '未分配' }}
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </template>
      <el-empty v-else description="用户不存在或已被删除" />
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const userId = ref<number>(parseInt(route.params.id as string))
const user = ref<any>(null)

// 根据角色获取对应的标签文字
const roleLabel = computed(() => {
  if (!user.value) return ''

  const roleMap: Record<string, string> = {
    'ADMIN': '管理员',
    'HEADTEACHER': '班主任',
    'TEACHER': '教师',
    'STUDENT': '学生'
  }

  return roleMap[user.value.role] || user.value.role
})

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString()
}

// 获取用户数据
const fetchUserData = async () => {
  if (!userId.value) return
  
  try {
    loading.value = true
    const userData = await userStore.fetchUserDetail(userId.value)
    
    if (userData) {
      user.value = userData
    } else {
      ElMessage.error('用户不存在')
      router.push('/user/list')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '获取用户信息失败')
  } finally {
    loading.value = false
  }
}

// 组件挂载时获取用户数据
onMounted(() => {
  fetchUserData()
})
</script>

<style lang="scss" scoped>
.user-detail-container {
  padding: 20px;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
    }
    
    .actions {
      display: flex;
      gap: 10px;
    }
  }

  .detail-card {
    max-width: 800px;
    margin: 0 auto;
  }
  
  .section-title {
    margin-top: 30px;
    margin-bottom: 15px;
    font-size: 18px;
    font-weight: 500;
    color: #606266;
    border-left: 4px solid #409eff;
    padding-left: 10px;
  }
}
</style> 