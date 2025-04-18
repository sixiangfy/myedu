<template>
  <div class="dashboard-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>欢迎使用教育管理系统</span>
            </div>
          </template>
          <div class="welcome-info">
            <p>您好，{{ authStore.roleName }}</p>
            <p>今天是 {{ currentDate }}</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="data-card">
          <div class="data-item">
            <div class="data-icon" style="background-color: #409EFF">
              <el-icon><User /></el-icon>
            </div>
            <div class="data-info">
              <div class="data-title">用户总数</div>
              <div class="data-value">{{ userCount }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="data-card">
          <div class="data-item">
            <div class="data-icon" style="background-color: #67C23A">
              <el-icon><Document /></el-icon>
            </div>
            <div class="data-info">
              <div class="data-title">考试次数</div>
              <div class="data-value">{{ examCount }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="data-card">
          <div class="data-item">
            <div class="data-icon" style="background-color: #E6A23C">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="data-info">
              <div class="data-title">平均分</div>
              <div class="data-value">{{ scoreStore.statistics.average || '-' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="data-card">
          <div class="data-item">
            <div class="data-icon" style="background-color: #F56C6C">
              <el-icon><Bell /></el-icon>
            </div>
            <div class="data-info">
              <div class="data-title">分析任务</div>
              <div class="data-value">{{ scoreStore.analysisTasks.length }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 成绩列表, 只对拥有权限的用户展示 -->
    <el-row v-if="authStore.hasTeacherAccess" :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近成绩</span>
              <el-button type="primary" size="small" @click="fetchScoreData">刷新</el-button>
            </div>
          </template>
          <el-table :data="scoreStore.filteredScoreList" v-loading="scoreStore.loading" style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="student_id" label="学生ID" width="100" />
            <el-table-column prop="exam_id" label="考试ID" width="100" />
            <el-table-column prop="subject_id" label="科目ID" width="100" />
            <el-table-column prop="score" label="成绩" width="100" />
            <el-table-column prop="ranking" label="排名" width="100" />
            <el-table-column prop="created_at" label="创建时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统公告</span>
            </div>
          </template>
          <el-table :data="announcements" style="width: 100%">
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="date" label="发布日期" width="180" />
            <el-table-column prop="author" label="发布人" width="120" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { User, Document, DataLine, Bell } from '@element-plus/icons-vue'
import { useAuthStore, useScoreStore } from '@/store'

// 使用Pinia store
const authStore = useAuthStore()
const scoreStore = useScoreStore()

// 获取当前日期
const currentDate = computed(() => {
  const date = new Date()
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
})

// 模拟数据
const userCount = ref(128)
const examCount = ref(32)

// 系统公告
const announcements = ref([
  {
    title: '关于期末考试安排的通知',
    date: '2023-06-10',
    author: '教务处'
  },
  {
    title: '系统更新维护通知',
    date: '2023-06-08',
    author: '系统管理员'
  },
  {
    title: '教师培训计划公告',
    date: '2023-06-05',
    author: '培训部'
  }
])

// 获取成绩数据
const fetchScoreData = async () => {
  await scoreStore.fetchScores()
}

// 获取分析任务
const fetchAnalysisTasks = async () => {
  await scoreStore.fetchAnalysisTasks()
}

// 组件挂载时获取数据
onMounted(async () => {
  // 获取数据，仅当用户有权限时加载
  if (authStore.hasTeacherAccess) {
    await fetchScoreData()
    await fetchAnalysisTasks()
  }
})
</script>

<style lang="scss" scoped>
.dashboard-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.welcome-info {
  font-size: 16px;
  line-height: 1.8;
}

.mt-20 {
  margin-top: 20px;
}

.data-card {
  margin-bottom: 20px;
}

.data-item {
  display: flex;
  align-items: center;
}

.data-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 15px;
  
  .el-icon {
    font-size: 30px;
    color: #fff;
  }
}

.data-info {
  .data-title {
    font-size: 14px;
    color: #909399;
    margin-bottom: 5px;
  }
  
  .data-value {
    font-size: 24px;
    font-weight: bold;
    color: #303133;
  }
}
</style> 