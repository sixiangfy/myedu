import { get, post, put, del } from '@/utils/request'

// 分析报告类型
export type AnalysisType = 'trend' | 'class_comparison' | 'subject_analysis' | 'student_growth'

// 分析报告接口
export interface AnalysisReport {
  id: number
  title: string
  type: AnalysisType
  target: string
  created_by: string
  created_at: string
  updated_at?: string
  content?: {
    chartData?: any
    summary?: Array<{
      label: string
      value: string | number
      trend?: 'up' | 'down' | 'flat'
    }>
  }
}

// 分析报告查询参数
export interface AnalysisReportQuery {
  page?: number
  limit?: number
  type?: AnalysisType
  dateRange?: [string, string]
  keyword?: string
}

// 创建分析报告参数
export interface CreateAnalysisReportParams {
  title: string
  type: AnalysisType
  target: string
  // 其他参数根据分析类型而定
  [key: string]: any
}

export interface AnalysisTask {
  id?: number
  title: string
  type: AnalysisType
  target: string
  params: Record<string, any>
}

/**
 * 获取分析报告列表
 */
export function getAnalysisReports(params: AnalysisReportQuery) {
  return get<{
    list: AnalysisReport[]
    total: number
  }>('/api/analysis/reports', params)
}

/**
 * 获取分析报告详情
 */
export function getAnalysisReport(id: number) {
  return get<AnalysisReport>(`/api/analysis/reports/${id}`)
}

/**
 * 创建分析报告
 * @param data 创建参数
 * @returns 创建的分析报告
 */
export function createAnalysisReport(data: CreateAnalysisReportParams) {
  return post<AnalysisReport>('/api/analysis/reports', data)
}

/**
 * 创建分析任务
 */
export function createAnalysisTask(data: AnalysisTask) {
  return post<AnalysisReport>('/api/analysis/tasks', data)
}

/**
 * 删除分析报告
 */
export function deleteAnalysisReport(id: number) {
  return del<boolean>(`/api/analysis/reports/${id}`)
}

/**
 * 导出分析报告
 */
export function exportAnalysisReport(id: number, format: 'pdf' | 'excel' = 'pdf') {
  return get<Blob>(`/api/analysis/reports/${id}/export`, { format }, {
    responseType: 'blob'
  })
}

/**
 * 生成趋势分析报告
 * @param data 分析参数
 * @returns 分析报告
 */
export function generateTrendAnalysis(data: {
  title: string
  target: string
  exam_ids: number[] // 考试ID列表
  subject_id?: number // 可选的学科ID，不指定则分析总分
}) {
  return get<AnalysisReport>('/api/analysis/generate/trend', {
    method: 'post',
    data
  })
}

/**
 * 生成班级对比分析报告
 * @param data 分析参数
 * @returns 分析报告
 */
export function generateClassComparisonAnalysis(data: {
  title: string
  exam_id: number // 考试ID
  class_ids: number[] // 班级ID列表
  subject_id?: number // 可选的学科ID，不指定则分析总分
}) {
  return get<AnalysisReport>('/api/analysis/generate/class-comparison', {
    method: 'post',
    data
  })
}

/**
 * 生成学科分析报告
 * @param data 分析参数
 * @returns 分析报告
 */
export function generateSubjectAnalysis(data: {
  title: string
  exam_id: number // 考试ID
  class_id: number // 班级ID
  subject_ids: number[] // 学科ID列表
}) {
  return get<AnalysisReport>('/api/analysis/generate/subject-analysis', {
    method: 'post',
    data
  })
}

/**
 * 生成学生成长分析报告
 * @param data 分析参数
 * @returns 分析报告
 */
export function generateStudentGrowthAnalysis(data: {
  title: string
  student_id: number // 学生ID
  exam_ids: number[] // 考试ID列表
  subject_id?: number // 可选的学科ID，不指定则分析总分
}) {
  return get<AnalysisReport>('/api/analysis/generate/student-growth', {
    method: 'post',
    data
  })
} 