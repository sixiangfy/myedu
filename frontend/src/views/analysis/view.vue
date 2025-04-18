<template>
  <div class="analysis-view-container page-container">
    <div class="page-header">
      <div class="header-title">
        <h2>{{ report ? report.title : '报告详情' }}</h2>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push('/analysis/list')">返回列表</el-button>
        <el-button type="primary" @click="exportReport('pdf')">
          <el-icon><Document /></el-icon>导出PDF
        </el-button>
      </div>
    </div>

    <el-card v-loading="loading" class="report-card">
      <template v-if="report">
        <div class="report-info">
          <div class="info-item">
            <span class="label">报告类型：</span>
            <el-tag :type="getTypeTagType(report.type)">{{ getTypeName(report.type) }}</el-tag>
          </div>
          <div class="info-item">
            <span class="label">分析对象：</span>
            <span>{{ report.target }}</span>
          </div>
          <div class="info-item">
            <span class="label">创建时间：</span>
            <span>{{ report.created_at }}</span>
          </div>
          <div class="info-item">
            <span class="label">创建人：</span>
            <span>{{ report.created_by }}</span>
          </div>
        </div>

        <el-divider>报告内容</el-divider>

        <div class="chart-container" ref="chartRef"></div>

        <el-divider>数据摘要</el-divider>

        <div class="summary-container">
          <div v-for="(item, index) in summaryData" :key="index" class="summary-item">
            <div class="summary-label">{{ item.label }}</div>
            <div class="summary-value" :class="item.type">{{ item.value }}</div>
          </div>
        </div>
      </template>
      <template v-else-if="!loading">
        <el-empty description="未找到报告数据" />
      </template>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { getAnalysisReport, deleteAnalysisReport, exportAnalysisReport, type AnalysisReport, type AnalysisType } from '@/api/analysis'
import { useLoading } from '@/store/loading'

// 路由
const route = useRoute()
const reportId = computed(() => Number(route.params.id))

// 状态
const loading = ref(false)
const report = ref<AnalysisReport | null>(null)
const summaryData = ref<{ label: string; value: string | number; type?: string }[]>([])

// 图表引用
const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

// 获取报告详情
const fetchReportDetail = async () => {
  if (!reportId.value) return

  try {
    loading.value = true
    const data = await getAnalysisReport(reportId.value)
    report.value = data

    // 设置摘要数据
    if (data.content && data.content.summary) {
      summaryData.value = data.content.summary.map((item: any) => ({
        label: item.label,
        value: item.value,
        type: getValueType(item.value, item.trend)
      }))
    }

    // 等待DOM更新后渲染图表
    setTimeout(() => {
      renderChart(data.content?.chartData || {})
    }, 100)
  } catch (error) {
    console.error('获取报告详情失败', error)
    ElMessage.error('获取报告详情失败')
  } finally {
    loading.value = false
  }
}

// 渲染图表
const renderChart = (chartData: any) => {
  if (!chartRef.value) return

  // 初始化图表
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  // 根据报告类型选择不同的图表配置
  let option: echarts.EChartsOption

  // 获取图表配置
  if (report.value) {
    switch (report.value.type) {
      case 'trend':
        option = getTrendChartOption(chartData)
        break
      case 'class_comparison':
        option = getComparisonChartOption(chartData)
        break
      case 'subject_analysis':
        option = getSubjectChartOption(chartData)
        break
      case 'student_growth':
        option = getGrowthChartOption(chartData)
        break
      default:
        option = getDefaultChartOption(chartData)
    }

    // 设置并渲染图表
    chart.setOption(option)
  }
}

// 趋势图配置
const getTrendChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '成绩趋势分析'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: data.legend || []
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
      data: data.xAxis || []
    },
    yAxis: {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100
    },
    series: data.series || []
  }
}

// 班级对比图配置
const getComparisonChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '班级对比分析'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: data.legend || []
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.xAxis || []
    },
    yAxis: {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100
    },
    series: data.series || []
  }
}

// 学科分析图配置
const getSubjectChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '学科分析'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: data.legend || []
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.xAxis || []
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
        name: '及格率',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    series: data.series || []
  }
}

// 学生成长图配置
const getGrowthChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '学生成长分析'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: data.legend || []
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.xAxis || []
    },
    yAxis: {
      type: 'value',
      name: '分数',
      min: 0,
      max: 100
    },
    series: data.series || []
  }
}

// 默认图表配置
const getDefaultChartOption = (data: any): echarts.EChartsOption => {
  return {
    title: {
      text: '分析报告'
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

// 导出报告
const exportReport = async (format: string) => {
  if (!report.value) return

  try {
    loading.value = true
    ElMessage.success(`报告《${report.value.title}》导出成功`)
    // 这里可以调用后端API执行实际导出操作
  } catch (error) {
    console.error('导出报告失败', error)
    ElMessage.error('导出报告失败')
  } finally {
    loading.value = false
  }
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

// 获取数值类型（用于样式）
const getValueType = (value: any, trend?: string): string => {
  if (trend === 'up') return 'positive'
  if (trend === 'down') return 'negative'
  if (typeof value === 'number') {
    return value >= 80 ? 'positive' : value >= 60 ? 'normal' : 'negative'
  }
  return 'normal'
}

// 窗口大小变化时重新调整图表
const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

// 组件挂载时
onMounted(() => {
  fetchReportDetail()
  window.addEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.analysis-view-container {
  .report-card {
    margin-bottom: 20px;
  }
  
  .report-info {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 20px;
    
    .info-item {
      display: flex;
      align-items: center;
      
      .label {
        font-weight: bold;
        margin-right: 8px;
        color: #606266;
      }
    }
  }
  
  .chart-container {
    height: 400px;
    margin-bottom: 20px;
  }
  
  .summary-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    
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

  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
      align-items: flex-start;
      
      .header-title {
        margin-bottom: 15px;
      }
      
      .header-actions {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
    }
    
    .chart-container {
      height: 300px;
    }
    
    .summary-item {
      min-width: 100% !important;
    }
  }
}
</style> 