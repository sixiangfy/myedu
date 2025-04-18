import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Score, GetScoresParams, AnalysisTask, AnalysisTaskType } from '@/types/api'
import { useAuthStore } from './auth'
import { ElMessage } from 'element-plus'

// 模拟API函数（实际项目中应从API模块导入）
// 获取成绩列表
const getScores = async (params: GetScoresParams) => {
  // 模拟请求
  return {
    data: [
      { id: 1, student_id: 1, exam_id: 1, subject_id: 1, score: 95, ranking: 1, created_at: '2023-06-01', updated_at: '2023-06-01' },
      { id: 2, student_id: 2, exam_id: 1, subject_id: 1, score: 88, ranking: 2, created_at: '2023-06-01', updated_at: '2023-06-01' },
      { id: 3, student_id: 3, exam_id: 1, subject_id: 1, score: 78, ranking: 3, created_at: '2023-06-01', updated_at: '2023-06-01' }
    ] as Score[],
    total: 3
  }
}

// 获取分析任务列表
const getAnalysisTasks = async () => {
  // 模拟请求
  return {
    data: [
      { id: 1, task_type: AnalysisTaskType.CLASS_BENCHMARK, status: 'completed', progress: 100, created_at: '2023-06-01', updated_at: '2023-06-01' },
      { id: 2, task_type: AnalysisTaskType.STUDENT_TREND, status: 'processing', progress: 50, created_at: '2023-06-02', updated_at: '2023-06-02' }
    ] as AnalysisTask[],
    total: 2
  }
}

export const useScoreStore = defineStore('score', () => {
  // 状态
  const scoreList = ref<Score[]>([])
  const currentScore = ref<Score | null>(null)
  const analysisTasks = ref<AnalysisTask[]>([])
  const currentAnalysisTask = ref<AnalysisTask | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(10)

  // 计算属性
  // 获取已过滤的成绩列表（基于权限）
  const filteredScoreList = computed(() => {
    const authStore = useAuthStore()
    
    // 管理员和教师可以看到所有成绩
    if (authStore.hasTeacherAccess) {
      return scoreList.value
    }
    
    // 学生只能看到自己的成绩
    return scoreList.value.filter(score => score.student_id.toString() === authStore.username)
  })

  // 统计信息
  const statistics = computed(() => {
    if (scoreList.value.length === 0) {
      return { average: 0, highest: 0, lowest: 0, passRate: 0 }
    }
    
    const scores = scoreList.value.map(item => item.score)
    const average = scores.reduce((sum, score) => sum + score, 0) / scores.length
    const highest = Math.max(...scores)
    const lowest = Math.min(...scores)
    const passCount = scores.filter(score => score >= 60).length
    const passRate = (passCount / scores.length) * 100
    
    return {
      average: parseFloat(average.toFixed(2)),
      highest,
      lowest,
      passRate: parseFloat(passRate.toFixed(2))
    }
  })

  // 方法
  // 获取成绩列表
  const fetchScores = async (params?: GetScoresParams) => {
    try {
      loading.value = true
      const pageParams = {
        page: params?.page || currentPage.value,
        page_size: params?.page_size || pageSize.value,
        exam_id: params?.exam_id,
        subject_id: params?.subject_id,
        student_id: params?.student_id,
        class_id: params?.class_id
      }
      
      const response = await getScores(pageParams)
      scoreList.value = response.data || []
      total.value = response.total || 0
      
      if (params?.page) {
        currentPage.value = params.page
      }
      if (params?.page_size) {
        pageSize.value = params.page_size
      }
      
      return scoreList.value
    } catch (error: any) {
      ElMessage.error(error.message || '获取成绩列表失败')
      return []
    } finally {
      loading.value = false
    }
  }

  // 获取分析任务列表
  const fetchAnalysisTasks = async () => {
    try {
      loading.value = true
      const response = await getAnalysisTasks()
      analysisTasks.value = response.data || []
      return analysisTasks.value
    } catch (error: any) {
      ElMessage.error(error.message || '获取分析任务列表失败')
      return []
    } finally {
      loading.value = false
    }
  }

  // 创建分析任务
  const createAnalysisTask = async (taskData: { task_type: AnalysisTaskType, target_ids: number[] }) => {
    // 检查权限
    const authStore = useAuthStore()
    if (!authStore.hasTeacherAccess) {
      ElMessage.error('您没有权限创建分析任务')
      return null
    }
    
    try {
      loading.value = true
      // 模拟API调用
      const newTask: AnalysisTask = {
        id: Date.now(),
        task_type: taskData.task_type,
        status: 'pending',
        progress: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      // 添加到任务列表
      analysisTasks.value = [...analysisTasks.value, newTask]
      currentAnalysisTask.value = newTask
      
      // 模拟任务处理
      setTimeout(() => {
        const index = analysisTasks.value.findIndex(task => task.id === newTask.id)
        if (index !== -1) {
          analysisTasks.value[index].status = 'processing'
          analysisTasks.value[index].progress = 50
        }
      }, 1000)
      
      setTimeout(() => {
        const index = analysisTasks.value.findIndex(task => task.id === newTask.id)
        if (index !== -1) {
          analysisTasks.value[index].status = 'completed'
          analysisTasks.value[index].progress = 100
        }
      }, 3000)
      
      return newTask
    } catch (error: any) {
      ElMessage.error(error.message || '创建分析任务失败')
      return null
    } finally {
      loading.value = false
    }
  }

  // 清除数据
  const clearScoreData = () => {
    scoreList.value = []
    currentScore.value = null
    analysisTasks.value = []
    currentAnalysisTask.value = null
    total.value = 0
    currentPage.value = 1
  }

  return {
    // 状态
    scoreList,
    currentScore,
    analysisTasks,
    currentAnalysisTask,
    total,
    loading,
    currentPage,
    pageSize,
    
    // 计算属性
    filteredScoreList,
    statistics,
    
    // 方法
    fetchScores,
    fetchAnalysisTasks,
    createAnalysisTask,
    clearScoreData
  }
}, {
  // 持久化配置 - 只持久化成绩数据
  persist: {
    key: 'score-store',
    storage: localStorage,
    paths: ['scoreList', 'currentPage', 'pageSize']
  }
}) 