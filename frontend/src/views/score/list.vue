<template>
  <div class="score-list-container">
    <div class="header">
      <h2>成绩列表</h2>
      <div class="header-actions">
        <el-button type="primary" @click="$router.push('/score/create')" v-if="authStore.hasTeacherAccess">
          添加成绩
        </el-button>
        <el-button type="success" @click="exportToExcel">
          <el-icon><Download /></el-icon>导出Excel
        </el-button>
        <el-upload
          class="excel-uploader"
          action="#"
          :http-request="handleExcelUpload"
          :show-file-list="false"
          accept=".xlsx,.xls"
        >
          <el-button type="warning" v-if="authStore.hasTeacherAccess">
            <el-icon><Upload /></el-icon>导入Excel
          </el-button>
        </el-upload>
      </div>
    </div>

    <el-card class="filter-card">
      <div class="filter-container">
        <el-select v-model="filter.exam_id" placeholder="考试" clearable>
          <el-option
            v-for="item in examOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>

        <el-select v-model="filter.subject_id" placeholder="科目" clearable>
          <el-option
            v-for="item in subjectOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>

        <el-select v-model="filter.class_id" placeholder="班级" clearable>
          <el-option
            v-for="item in classOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>

        <el-input
          v-model="filter.student_name"
          placeholder="学生姓名"
          clearable
          style="width: 200px"
        />

        <el-button type="primary" @click="fetchScores">搜索</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="scoreList"
        border
        style="width: 100%"
      >
        <el-table-column prop="student_name" label="学生姓名" min-width="120" />
        <el-table-column prop="exam_name" label="考试" min-width="150" />
        <el-table-column prop="subject_name" label="科目" min-width="100" />
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column prop="score" label="分数" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row.score)">{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ranking" label="排名" width="80" />
        <el-table-column prop="created_at" label="录入时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="primary" 
              @click="$router.push(`/score/edit/${row.id}`)"
              v-if="authStore.hasTeacherAccess"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              v-if="authStore.hasTeacherAccess"
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

    <!-- 班级成绩对比卡片 -->
    <el-card class="comparison-card" v-if="filter.exam_id && filter.subject_id">
      <div class="card-header">
        <h3>班级成绩对比</h3>
      </div>
      <div class="chart-container" ref="chartRef"></div>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, UploadRequestOptions } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store'
import { 
  getScores, 
  deleteScore, 
  exportScores,
  importScores
} from '@/api/score'
import { 
  getExams, 
  getSubjects, 
  getClasses 
} from '@/api/common'
import * as echarts from 'echarts'

// 使用store
const authStore = useAuthStore()

// 图表引用
const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

// 分页和加载状态
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)

// 成绩列表
const scoreList = ref<any[]>([])

// 筛选条件
const filter = reactive({
  exam_id: undefined as number | undefined,
  subject_id: undefined as number | undefined,
  class_id: undefined as number | undefined,
  student_name: ''
})

// 选项数据
const examOptions = ref<{ value: number; label: string }[]>([])
const subjectOptions = ref<{ value: number; label: string }[]>([])
const classOptions = ref<{ value: number; label: string }[]>([])

// 获取成绩数据
const fetchScores = async () => {
  try {
    loading.value = true
    
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ...filter
    }
    
    const response = await getScores(params)
    scoreList.value = response.data || []
    total.value = response.total || 0
    
    // 如果已选择考试和科目，更新班级对比图表
    if (filter.exam_id && filter.subject_id) {
      updateComparisonChart()
    }
  } catch (error) {
    console.error('获取成绩列表失败', error)
    ElMessage.error('获取成绩列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilter = () => {
  Object.keys(filter).forEach(key => {
    filter[key as keyof typeof filter] = key === 'student_name' ? '' : undefined
  })
  currentPage.value = 1
  fetchScores()
}

// 处理页数变化
const handleSizeChange = () => {
  fetchScores()
}

// 处理页码变化
const handleCurrentChange = () => {
  fetchScores()
}

// 处理删除成绩
const handleDelete = (row: any) => {
  ElMessageBox.confirm(
    `确定要删除该成绩记录吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteScore(row.id)
      ElMessage.success('删除成功')
      fetchScores()
    } catch (error) {
      console.error('删除成绩失败', error)
      ElMessage.error('删除成绩失败')
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// 导出成绩到Excel
const exportToExcel = async () => {
  try {
    loading.value = true
    const params = { ...filter }
    
    // 调用导出API
    const blob = await exportScores(params)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `成绩导出_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    
    // 释放URL对象
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出成绩失败', error)
    ElMessage.error('导出成绩失败')
  } finally {
    loading.value = false
  }
}

// 处理Excel上传
const handleExcelUpload = async (options: UploadRequestOptions) => {
  const file = options.file
  if (!file) return
  
  try {
    loading.value = true
    
    const formData = new FormData()
    formData.append('file', file)
    
    // 如果有筛选条件，添加到表单数据中
    if (filter.exam_id) {
      formData.append('exam_id', filter.exam_id.toString())
    }
    if (filter.subject_id) {
      formData.append('subject_id', filter.subject_id.toString())
    }
    
    // 调用导入API
    const result = await importScores(formData)
    
    ElMessage.success(`成功导入 ${result.imported_count} 条成绩记录`)
    fetchScores() // 刷新列表
  } catch (error) {
    console.error('导入成绩失败', error)
    ElMessage.error('导入成绩失败')
  } finally {
    loading.value = false
  }
}

// 获取考试、科目和班级选项
const fetchOptions = async () => {
  try {
    // 获取考试列表
    const exams = await getExams()
    examOptions.value = exams.map(exam => ({
      value: exam.id,
      label: exam.name
    }))
    
    // 获取科目列表
    const subjects = await getSubjects()
    subjectOptions.value = subjects.map(subject => ({
      value: subject.id,
      label: subject.name
    }))
    
    // 获取班级列表
    const classes = await getClasses()
    classOptions.value = classes.map(cls => ({
      value: cls.id,
      label: cls.name
    }))
  } catch (error) {
    console.error('获取选项数据失败', error)
    ElMessage.error('获取选项数据失败')
  }
}

// 获取成绩样式
const getScoreClass = (score: number) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

// 更新班级对比图表
const updateComparisonChart = async () => {
  if (!filter.exam_id || !filter.subject_id) return
  
  try {
    // 1. 获取班级成绩数据
    const classScores = await getClassScoresComparison(filter.exam_id, filter.subject_id)
    
    // 2. 等待DOM更新
    await nextTick()
    
    // 3. 初始化图表
    if (!chartRef.value) return
    
    if (!chart) {
      chart = echarts.init(chartRef.value)
    }
    
    // 4. 设置图表配置
    const option = {
      title: {
        text: '班级成绩对比'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['平均分', '最高分', '最低分', '及格率']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: [
        {
          type: 'category',
          data: classScores.map(item => item.class_name)
        }
      ],
      yAxis: [
        {
          type: 'value',
          name: '分数',
          min: 0,
          max: 100
        },
        {
          type: 'value',
          name: '及格率',
          min: 0,
          max: 100,
          axisLabel: {
            formatter: '{value}%'
          }
        }
      ],
      series: [
        {
          name: '平均分',
          type: 'bar',
          data: classScores.map(item => item.avg_score)
        },
        {
          name: '最高分',
          type: 'bar',
          data: classScores.map(item => item.max_score)
        },
        {
          name: '最低分',
          type: 'bar',
          data: classScores.map(item => item.min_score)
        },
        {
          name: '及格率',
          type: 'line',
          yAxisIndex: 1,
          data: classScores.map(item => item.pass_rate)
        }
      ]
    }
    
    // 5. 渲染图表
    chart.setOption(option)
  } catch (error) {
    console.error('更新班级对比图表失败', error)
  }
}

// 获取班级成绩对比数据（模拟API）
const getClassScoresComparison = async (examId: number, subjectId: number) => {
  // 实际中应该调用API
  // 这里返回模拟数据
  return [
    { 
      class_id: 1, 
      class_name: '高一(1)班', 
      avg_score: 85.6, 
      max_score: 98, 
      min_score: 62, 
      pass_rate: 96.7 
    },
    { 
      class_id: 2, 
      class_name: '高一(2)班', 
      avg_score: 82.1, 
      max_score: 95, 
      min_score: 55, 
      pass_rate: 91.2 
    },
    { 
      class_id: 3, 
      class_name: '高一(3)班', 
      avg_score: 79.8, 
      max_score: 96, 
      min_score: 51, 
      pass_rate: 88.5 
    },
    { 
      class_id: 4, 
      class_name: '高一(4)班', 
      avg_score: 83.2, 
      max_score: 97, 
      min_score: 59, 
      pass_rate: 93.4 
    }
  ]
}

// 监听筛选条件变化
watch([() => filter.exam_id, () => filter.subject_id], () => {
  if (filter.exam_id && filter.subject_id) {
    // 延迟一下等DOM更新
    setTimeout(() => {
      updateComparisonChart()
    }, 100)
  }
})

// 组件挂载时
onMounted(() => {
  fetchOptions()
  fetchScores()
  
  // 窗口大小变化时重新调整图表
  window.addEventListener('resize', () => {
    if (chart) {
      chart.resize()
    }
  })
})
</script>

<style lang="scss" scoped>
.score-list-container {
  padding: 20px;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
    }
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .filter-card {
    margin-bottom: 20px;
    
    .filter-container {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
  }

  .table-card {
    margin-bottom: 20px;
  }

  .comparison-card {
    margin-bottom: 20px;
    
    .card-header {
      margin-bottom: 15px;
      
      h3 {
        margin: 0;
      }
    }
    
    .chart-container {
      height: 400px;
    }
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }
  
  .score-excellent {
    color: #67C23A;
    font-weight: bold;
  }
  
  .score-good {
    color: #409EFF;
    font-weight: bold;
  }
  
  .score-pass {
    color: #E6A23C;
  }
  
  .score-fail {
    color: #F56C6C;
    font-weight: bold;
  }
}
</style> 