<template>
  <div class="user-list-container">
    <div class="header">
      <h2>用户列表</h2>
      <el-button 
        v-if="authStore.hasAdminAccess" 
        type="primary" 
        @click="$router.push('/user/create')"
      >
        创建用户
      </el-button>
    </div>

    <el-card class="table-card">
      <div class="filter-container">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名/邮箱"
          clearable
          style="width: 200px"
          @clear="handleFilter"
          @keyup.enter="handleFilter"
        />
        <el-select v-model="roleFilter" placeholder="角色" clearable style="width: 120px" @change="handleFilter">
          <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" @click="handleFilter">搜索</el-button>
      </div>

      <el-table
        v-loading="userStore.loading"
        :data="filteredUsers"
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="role" label="角色">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">{{ getRoleName(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="is_active" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="primary" 
              @click="$router.push(`/user/edit/${row.id}`)"
              v-if="authStore.hasAdminAccess"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              v-if="authStore.hasAdminAccess"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore, useAuthStore } from '@/store'
import { User, UserRole } from '@/types/api'
import { deleteUser } from '@/api/user'

// 使用store
const userStore = useUserStore()
const authStore = useAuthStore()

// 页面状态
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchQuery = ref('')
const roleFilter = ref('')

// 角色选项
const roleOptions = [
  { value: UserRole.ADMIN, label: '管理员' },
  { value: UserRole.HEADTEACHER, label: '班主任' },
  { value: UserRole.TEACHER, label: '教师' },
  { value: UserRole.STUDENT, label: '学生' }
]

// 获取角色标签类型
const getRoleTagType = (role: string) => {
  const map: Record<string, string> = {
    [UserRole.ADMIN]: 'danger',
    [UserRole.HEADTEACHER]: 'warning',
    [UserRole.TEACHER]: 'success',
    [UserRole.STUDENT]: 'info'
  }
  return map[role] || 'info'
}

// 获取角色名称
const getRoleName = (role: string) => {
  const map: Record<string, string> = {
    [UserRole.ADMIN]: '管理员',
    [UserRole.HEADTEACHER]: '班主任',
    [UserRole.TEACHER]: '教师',
    [UserRole.STUDENT]: '学生'
  }
  return map[role] || '未知'
}

// 过滤用户列表
const filteredUsers = computed(() => {
  let users = userStore.filteredUserList
  
  // 应用搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    users = users.filter(user => 
      user.username.toLowerCase().includes(query) || 
      (user.email && user.email.toLowerCase().includes(query))
    )
  }
  
  // 应用角色过滤
  if (roleFilter.value) {
    users = users.filter(user => user.role === roleFilter.value)
  }
  
  return users
})

// 处理筛选
const handleFilter = () => {
  currentPage.value = 1
  fetchUsers()
}

// 处理页数变化
const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchUsers()
}

// 处理页码变化
const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchUsers()
}

// 获取用户数据
const fetchUsers = async () => {
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    await userStore.fetchUsers(params)
    total.value = userStore.total
  } catch (error) {
    console.error('获取用户列表失败', error)
    ElMessage.error('获取用户列表失败')
  }
}

// 处理删除用户
const handleDelete = (row: User) => {
  ElMessageBox.confirm(
    `确定要删除用户 "${row.username}" 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteUser(row.id)
      ElMessage.success('删除成功')
      fetchUsers()
    } catch (error) {
      console.error('删除用户失败', error)
      ElMessage.error('删除用户失败')
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 监听过滤器变化自动刷新列表
watch([searchQuery, roleFilter], () => {
  if (userStore.userList.length > 0) {
    handleFilter()
  }
})

// 初始加载
onMounted(() => {
  fetchUsers()
})
</script>

<style lang="scss" scoped>
.user-list-container {
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

  .table-card {
    margin-bottom: 20px;
  }

  .filter-container {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }
}
</style> 