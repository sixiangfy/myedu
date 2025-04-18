<template>
  <div class="analysis-create-container">
    <div class="header">
      <h2>创建分析报告</h2>
      <el-button @click="$router.push('/analysis/list')">返回列表</el-button>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <h3>分析配置</h3>
            </div>
          </template>
          
          <el-form 
            ref="formRef" 
            :model="formData" 
            :rules="formRules" 
            label-width="100px"
            label-position="top"
          >
            <el-form-item label="分析类型" prop="task_type">
              <el-select v-model="formData.task_type" placeholder="请选择分析类型" style="width: 100%">
                <el-option
                  v-for="item in analysisTypeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="分析目标" prop="target_ids">
              <el-select 
                v-model="formData.target_ids" 
                multiple 
                :placeholder="getTargetPlaceholder" 
                style="width: 100%"
              >
                <el-option
                  v-for="item in targetOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="科目" prop="subject_ids">
              <el-select 
                v-model="formData.subject_ids" 
                multiple 
                placeholder="请选择科目" 
                style="width: 100%"
              >
                <el-option
                  v-for="item in subjectOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="考试" prop="exam_ids">
              <el-select 
                v-model="formData.exam_ids" 
                multiple 
                placeholder="请选择考试" 
                style="width: 100%"
              >
                <el-option
                  v-for="item in examOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="时间范围" prop="time_range">
              <el-date-picker
                v-model="timeRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="handlePreview" :loading="loading">预览</el-button>
              <el-button type="success" @click="handleGenerate" :loading="generating">生成报告</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <h3>分析预览</h3>
              <div class="action-buttons" v-if="chartReady">
                <el-button type="primary" size="small" @click="exportChart('png')">
                  <el-icon><Download /></el-icon>导出PNG
                </el-button>
                <el-button type="success" size="small" @click="exportChart('pdf')">
                  <el-icon><Document /></el-icon>导出PDF
                </el-button>
              </div>
            </div>
          </template>
          
          <div v-if="!chartReady" class="empty-chart">
            <el-empty description="请配置分析参数并点击预览" />
          </div>
          
          <div v-else>
            <div class="chart-container" ref="chartRef"></div>
            
            <el-divider>数据摘要</el-divider>
            
            <div class="summary-container">
              <div v-for="(item, index) in dataSummary" :key="index" class="summary-item">
                <div class="summary-label">{{ item.label }}</div>
                <div class="summary-value" :class="item.type">{{ item.value }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Download, Document } from '@element-plus/icons-vue'
import { AnalysisTaskType, AnalysisTaskParams } from '@/types/api'
import { createAnalysisTask, previewAnalysis, exportAnalysisChart } from '@/api/analysis'
import { getExams, getSubjects, getClasses, getStudents } from '@/api/common'
import * as echarts from 'echarts'

// 引入路由
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()

// 图表引用
const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

// 状态
const loading = ref(false)
const generating = ref(false)
const chartReady = ref(false)

// 时间范围 (用于日期选择器)
const timeRange = ref<[string, string] | null>(null)

// 预览数据
const dataSummary = ref<{ label: string; value: string | number; type?: string }[]>([])

// 下拉选项
const analysisTypeOptions = [
  { value: AnalysisTaskType.CLASS_BENCHMARK, label: '班级基准分析' },
  { value: AnalysisTaskType.STUDENT_TREND, label: '学生趋势分析' },
  { value: AnalysisTaskType.COMPARATIVE, label: '对比分析' },
  { value: AnalysisTaskType.COMPREHENSIVE, label: '综合分析' }
]

// 动态选项
const subjectOptions = ref<{ value: number; label: string }[]>([])
const examOptions = ref<{ value: number; label: string }[]>([])
const targetOptions = ref<{ value: number; label: string }[]>([])

// 表单数据
const formData = reactive<AnalysisTaskParams>({
  task_type: AnalysisTaskType.STUDENT_TREND,
  target_ids: [],
  subject_ids: [],
  exam_ids: [],
  time_range: undefined,
  parameters: {}
})

// 表单验证规则
const formRules = reactive<FormRules>({
  task_type: [
    { required: true, message: '请选择分析类型', trigger: 'change' }
  ],
  target_ids: [
    { required: true, message: '请选择分析目标', trigger: 'change' }
  ],
  subject_ids: [
    { type: 'array', message: '请选择科目', trigger: 'change' }
  ],
  exam_ids: [
    { type: 'array', message: '请选择考试', trigger: 'change' }
  ]
})

// 获取目标提示文本
const getTargetPlaceholder = computed(() => {
  switch (formData.task_type) {
    case AnalysisTaskType.CLASS_BENCHMARK:
      return '请选择班级'
    case AnalysisTaskType.STUDENT_TREND:
      return '请选择学生'
    case AnalysisTaskType.COMPARATIVE:
      return '请选择比较对象'
    default:
      return '请选择分析目标'
  }
})

// 获取下拉选项数据
const fetchOptions = async () => {
  try {
    loading.value = true
    
    // 获取科目列表
    const subjects = await getSubjects()
    subjectOptions.value = subjects.map(subject => ({
      value: subject.id,
      label: subject.name
    }))
    
    // 获取考试列表
    const exams = await getExams()
    examOptions.value = exams.map(exam => ({
      value: exam.id,
      label: exam.name
    }))
    
    // 根据分析类型设置目标选项
    await updateTargetOptions()
  } catch (error) {
    console.error('获取选项数据失败', error)
    ElMessage.error('获取选项数据失败')
  } finally {
    loading.value = false
  }
}

// 更新目标选项
const updateTargetOptions = async () => {
  try {
    // 清空现有选项和选择
    targetOptions.value = []
    formData.target_ids = []
    
    // 根据分析类型获取相应的目标选项
    switch (formData.task_type) {
      case AnalysisTaskType.CLASS_BENCHMARK:
        // 获取班级列表作为目标
        const classes = await getClasses()
        targetOptions.value = classes.map(cls => ({
          value: cls.id,
          label: cls.name
        }))
        break
        
      case AnalysisTaskType.STUDENT_TREND:
      case AnalysisTaskType.COMPARATIVE:
        // 获取学生列表作为目标
        const students = await getStudents()
        targetOptions.value = students.map(student => ({
          value: student.id,
          label: student.name
        }))
        break
        
      case AnalysisTaskType.COMPREHENSIVE:
        // 综合分析可以选择班级
        const classesForComp = await getClasses()
        targetOptions.value = classesForComp.map(cls => ({
          value: cls.id,
          label: cls.name
        }))
        break
    }
  } catch (error) {
    console.error('更新目标选项失败', error)
    ElMessage.error('获取分析目标失败')
  }
}

// 处理预览
const handlePreview = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true
        
        // 设置时间范围
        if (timeRange.value) {
          formData.time_range = {
            start_time: timeRange.value[0],
            end_time: timeRange.value[1]
          }
        }
        
        // 调用预览API
        const previewData = await previewAnalysis(formData)
        
        // 显示图表
        await renderChart(previewData.chartData)
        
        // 设置数据摘要
        dataSummary.value = previewData.summary.map((item: any) => ({
          label: item.label,
          value: item.value,
          type: getValueType(item.value, item.trend)
        }))
        
        chartReady.value = true
      } catch (error) {
        console.error('预览分析失败', error)
        ElMessage.error('预览分析失败')
      } finally {
        loading.value = false
      }
    }
  })
}

// 处理生成报告
const handleGenerate = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        generating.value = true
        
        // 设置时间范围
        if (timeRange.value) {
          formData.time_range = {
            start_time: timeRange.value[0],
            end_time: timeRange.value[1]
          }
        }
        
        // 调用创建分析任务API
        const result = await createAnalysisTask(formData)
        
        ElMessage.success('分析任务创建成功')
        router.push(`/analysis/view/${result.id}`)
      } catch (error) {
        console.error('创建分析任务失败', error)
        ElMessage.error('创建分析任务失败')
      } finally {
        generating.value = false
      }
    }
  })
}

// 渲染图表
const renderChart = async (chartData: any) => {
  // 等待DOM更新
  await nextTick()
  
  // 初始化图表
  if (!chartRef.value) return
  
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  
  // 根据分析类型选择不同的图表配置
  let option: echarts.EChartsOption
  
  switch (formData.task_type) {
    case AnalysisTaskType.STUDENT_TREND:
      option = getStudentTrendChartOption(chartData)
      break
    case AnalysisTaskType.COMPARATIVE:
      option = getComparativeChartOption(chartData)
      break
    case AnalysisTaskType.CLASS_BENCHMARK:
      option = getClassBenchmarkChartOption(chartData)
      break
    case AnalysisTaskType.COMPREHENSIVE:
      option = getComprehensiveChartOption(chartData)
      break
    default:
      option = getDefaultChartOption(chartData)
  }
  
  // 设置并渲染图表
  chart.setOption(option)
}

// 学生趋势图配置
const getStudentTrendChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '学生成绩趋势分析'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: data.legend
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.xAxis
    },
    yAxis: {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100
    },
    series: data.series
  }
}

// 对比分析图配置
const getComparativeChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '成绩对比分析'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: data.legend
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.xAxis
    },
    yAxis: {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100
    },
    series: data.series
  }
}

// 班级基准分析图配置
const getClassBenchmarkChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '班级基准分析'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: data.legend
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.xAxis
    },
    yAxis: [
      {
        type: 'value',
        name: '分数',
        min: 0,
        max: 100
      },
      {
        type: 'value',
        name: '百分比',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    series: data.series
  }
}

// 综合分析图配置
const getComprehensiveChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '综合成绩分析'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    radar: {
      indicator: data.radar.indicator
    },
    series: [
      {
        type: 'radar',
        data: data.radar.data
      }
    ]
  }
}

// 默认图表配置
const getDefaultChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '成绩分析'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.xAxis || []
    },
    yAxis: {
      type: 'value'
    },
    series: data.series || []
  }
}

// 导出图表
const exportChart = async (type: 'png' | 'pdf') => {
  try {
    loading.value = true
    
    if (type === 'png' && chart) {
      // 直接导出PNG
      const url = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })
      
      const link = document.createElement('a')
      link.href = url
      link.download = `分析报告_${new Date().toISOString().split('T')[0]}.png`
      link.click()
    } else {
      // 调用API导出PDF
      const result = await exportAnalysisChart({
        chart_data: chart?.getOption() || {},
        format: type,
        title: getChartTitle(),
        summary: dataSummary.value
      })
      
      // 处理下载
      const url = window.URL.createObjectURL(result)
      const link = document.createElement('a')
      link.href = url
      link.download = `分析报告_${new Date().toISOString().split('T')[0]}.${type}`
      link.click()
      
      // 释放URL对象
      window.URL.revokeObjectURL(url)
    }
    
    ElMessage.success(`导出${type.toUpperCase()}成功`)
  } catch (error) {
    console.error(`导出${type}失败`, error)
    ElMessage.error(`导出${type}失败`)
  } finally {
    loading.value = false
  }
}

// 获取图表标题
const getChartTitle = (): string => {
  const typeMap: Record<string, string> = {
    [AnalysisTaskType.STUDENT_TREND]: '学生成绩趋势分析',
    [AnalysisTaskType.COMPARATIVE]: '成绩对比分析',
    [AnalysisTaskType.CLASS_BENCHMARK]: '班级基准分析',
    [AnalysisTaskType.COMPREHENSIVE]: '综合成绩分析'
  }
  
  return typeMap[formData.task_type] || '成绩分析'
}

// 获取数值类型（用于样式）
const getValueType = (value: any, trend?: string): string => {
  if (trend === 'up') return 'positive'
  if (trend === 'down') return 'negative'
  if (typeof value === 'number') {
    return value >= 80 ? 'positive' : value >= 60 ? 'normal' : 'negative'
  }
  return 'normal'
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  
  timeRange.value = null
  chartReady.value = false
  
  if (chart) {
    chart.clear()
  }
}

// 监听分析类型变化
watch(() => formData.task_type, async () => {
  await updateTargetOptions()
})

// 组件挂载时
onMounted(() => {
  fetchOptions()
  
  // 窗口大小变化时重新调整图表
  window.addEventListener('resize', () => {
    if (chart) {
      chart.resize()
    }
  })
})
</script>

<style lang="scss" scoped>
.analysis-create-container {
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
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    h3 {
      margin: 0;
    }
    
    .action-buttons {
      display: flex;
      gap: 10px;
    }
  }
  
  .config-card,
  .chart-card {
    margin-bottom: 20px;
    height: calc(100vh - 150px);
    overflow-y: auto;
  }
  
  .empty-chart {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 400px;
  }
  
  .chart-container {
    height: 400px;
  }
  
  .summary-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-top: 20px;
    
    .summary-item {
      flex: 1;
      min-width: 150px;
      
      .summary-label {
        font-size: 14px;
        color: #909399;
        margin-bottom: 5px;
      }
      
      .summary-value {
        font-size: 18px;
        font-weight: bold;
        
        &.positive {
          color: #67C23A;
        }
        
        &.negative {
          color: #F56C6C;
        }
        
        &.normal {
          color: #409EFF;
        }
      }
    }
  }
}
</style> 