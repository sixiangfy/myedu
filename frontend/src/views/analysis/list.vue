<template>
  <div class="analysis-list-container">
    <div class="header">
      <h2>分析报告</h2>
      <div class="header-actions">
        <el-button type="primary" @click="$router.push('/analysis/create')">
          创建分析任务
        </el-button>
      </div>
    </div>
    
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="报告类型">
          <el-select v-model="filterForm.type" placeholder="所有类型" clearable>
            <el-option label="成绩趋势" value="trend" />
            <el-option label="班级对比" value="class_comparison" />
            <el-option label="学科分析" value="subject_analysis" />
            <el-option label="个人成长" value="student_growth" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="创建日期">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card class="table-card" v-loading="loading">
      <el-table
        :data="analysisReports"
        style="width: 100%"
        border
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="报告标题" min-width="180" />
        <el-table-column prop="type" label="分析类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">{{ getTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="分析对象" width="150" />
        <el-table-column prop="created_by" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="$router.push(`/analysis/view/${row.id}`)"
              text
            >
              查看
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row.id)"
              :disabled="!authStore.hasTeacherAccess"
              text
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
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="fetchAnalysisReports"
          @current-change="fetchAnalysisReports"
        />
      </div>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/store'
import { 
  getAnalysisReports, 
  deleteAnalysisReport,
  AnalysisReport,
  AnalysisType 
} from '@/api/analysis'

// 使用store
const authStore = useAuthStore()

// 加载状态
const loading = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 分析报告列表
const analysisReports = ref<AnalysisReport[]>([])

// 筛选表单
const filterForm = reactive({
  type: '',
  dateRange: [] as string[]
})

// 获取分析报告列表
const fetchAnalysisReports = async () => {
  try {
    loading.value = true
    
    // 准备查询参数
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    // 添加筛选条件
    if (filterForm.type) {
      params.type = filterForm.type
    }
    
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }
    
    // 调用API获取数据
    const { items, total: totalCount } = await getAnalysisReports(params)
    analysisReports.value = items
    total.value = totalCount
  } catch (error) {
    console.error('获取分析报告失败', error)
    ElMessage.error('获取分析报告失败')
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchAnalysisReports()
}

// 重置筛选
const resetFilter = () => {
  filterForm.type = ''
  filterForm.dateRange = []
  handleSearch()
}

// 删除分析报告
const handleDelete = (id: number) => {
  ElMessageBox.confirm(
    '此操作将永久删除该分析报告, 是否继续?',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      loading.value = true
      await deleteAnalysisReport(id)
      ElMessage.success('删除成功')
      fetchAnalysisReports()
    } catch (error) {
      console.error('删除分析报告失败', error)
      ElMessage.error('删除分析报告失败')
    } finally {
      loading.value = false
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 获取分析类型名称
const getTypeName = (type: AnalysisType) => {
  const typeMap: Record<AnalysisType, string> = {
    trend: '成绩趋势',
    class_comparison: '班级对比',
    subject_analysis: '学科分析',
    student_growth: '个人成长'
  }
  return typeMap[type] || type
}

// 获取分析类型标签样式
const getTypeTagType = (type: AnalysisType) => {
  const typeTagMap: Record<AnalysisType, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    trend: '',
    class_comparison: 'success',
    subject_analysis: 'warning',
    student_growth: 'info'
  }
  return typeTagMap[type] || ''
}

// 组件挂载时获取数据
onMounted(() => {
  fetchAnalysisReports()
})
</script>

<style lang="scss" scoped>
.analysis-list-container {
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
  
  .filter-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    margin-bottom: 20px;
  }
  
  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style> 