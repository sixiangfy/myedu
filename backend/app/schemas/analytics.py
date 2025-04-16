from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class AnalysisTaskStatus(str, Enum):
    """分析任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisTaskType(str, Enum):
    """分析任务类型"""
    CLASS_BENCHMARK = "class_benchmark"    # 班级教学水平评估
    STUDENT_TREND = "student_trend"        # 学生个人成长轨迹
    COMPARATIVE = "comparative"            # 跨班级/跨年级对比
    COMPREHENSIVE = "comprehensive"        # 综合分析

class AnalysisReportFormat(str, Enum):
    """分析报告格式"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    JSON = "json"

class AnalysisTaskCreate(BaseModel):
    """创建分析任务模型"""
    task_type: AnalysisTaskType = Field(..., description="分析任务类型")
    target_ids: List[int] = Field(..., description="目标ID列表(学生/班级/年级)")
    subject_ids: Optional[List[int]] = Field(None, description="学科ID列表")
    exam_ids: Optional[List[int]] = Field(None, description="考试ID列表")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="时间范围")
    parameters: Optional[Dict[str, Any]] = Field(None, description="附加参数")

class AnalysisTaskResponse(BaseModel):
    """分析任务响应模型"""
    id: int = Field(..., description="任务ID")
    task_type: AnalysisTaskType = Field(..., description="分析任务类型")
    status: AnalysisTaskStatus = Field(..., description="任务状态")
    progress: int = Field(0, description="任务进度(百分比)")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    results_url: Optional[str] = Field(None, description="结果URL")
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ClassBenchmarkData(BaseModel):
    """班级标杆分析数据"""
    class_id: int = Field(..., description="班级ID")
    class_name: str = Field(..., description="班级名称")
    grade_name: str = Field(..., description="年级名称")
    exam_name: str = Field(..., description="考试名称")
    total_students: int = Field(..., description="学生总数")
    stats_by_subject: Dict[str, Dict[str, Any]] = Field(..., description="各科目统计数据")
    overall_stats: Dict[str, Any] = Field(..., description="总体统计数据")
    
    class Config:
        from_attributes = True
        populate_by_name = True

class StudentTrendData(BaseModel):
    """学生成长轨迹数据"""
    student_id: int = Field(..., description="学生ID")
    student_name: str = Field(..., description="学生姓名")
    student_code: str = Field(..., description="学号")
    class_name: str = Field(..., description="班级名称")
    exam_scores: List[Dict[str, Any]] = Field(..., description="各考试成绩")
    trend_data: Dict[str, List[float]] = Field(..., description="趋势数据")
    radar_data: Dict[str, List[float]] = Field(..., description="雷达图数据")
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ComparativeAnalysisData(BaseModel):
    """对比分析数据"""
    subject_name: str = Field(..., description="学科名称")
    comparison_type: str = Field(..., description="对比类型(班级/年级)")
    target_names: List[str] = Field(..., description="目标名称列表")
    average_scores: Dict[str, float] = Field(..., description="平均分对比")
    pass_rates: Dict[str, float] = Field(..., description="及格率对比")
    excellent_rates: Dict[str, float] = Field(..., description="优秀率对比")
    score_distributions: Dict[str, Dict[str, int]] = Field(..., description="分数段分布对比")
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ExportRequest(BaseModel):
    """导出请求模型"""
    report_type: str = Field(..., description="报告类型")
    format: AnalysisReportFormat = Field(..., description="导出格式")
    data_id: int = Field(..., description="数据ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="附加参数")

class GradeRankData(BaseModel):
    """年级排名数据"""
    absolute_rank: int = Field(..., description="绝对排名（如15/300中的15）")
    total_students: int = Field(..., description="总学生数（如15/300中的300）")
    percentage: float = Field(..., description="百分比位置（如前5%）")
    percentile: float = Field(..., description="百分位数（如95表示超过95%的学生）")

class DualRankData(BaseModel):
    """双维度排名数据"""
    class_rank: int = Field(..., description="班级排名（如2/40中的2）")
    class_total: int = Field(..., description="班级总人数（如2/40中的40）")
    grade_rank: int = Field(..., description="年级排名（如150/1200中的150）")
    grade_total: int = Field(..., description="年级总人数（如150/1200中的150）")
    class_percentile: float = Field(..., description="班级百分位数")
    grade_percentile: float = Field(..., description="年级百分位数")

class RankHistory(BaseModel):
    """排名历史记录"""
    exam_id: int = Field(..., description="考试ID")
    exam_name: str = Field(..., description="考试名称")
    exam_date: datetime = Field(..., description="考试日期")
    class_rank: int = Field(..., description="班级排名")
    class_total: int = Field(..., description="班级总人数")
    grade_rank: int = Field(..., description="年级排名")
    grade_total: int = Field(..., description="年级总人数")

class ScoreLevel(str, Enum):
    """成绩段位类型"""
    EXCELLENT = "excellent"  # 优秀：总分80%（含80%）
    GOOD = "good"            # 良好：总分70%（含70%）
    PASS = "pass"            # 及格：总分60%（含60%）
    FAIL = "fail"            # 不及格：低于总分60%（不含60%）

class LevelDistribution(BaseModel):
    """段位分布数据"""
    level: ScoreLevel = Field(..., description="段位类型")
    count: int = Field(..., description="该段位人数")
    percentage: float = Field(..., description="该段位占比")

class ClassLevelDistribution(BaseModel):
    """班级段位分布"""
    class_id: int = Field(..., description="班级ID")
    class_name: str = Field(..., description="班级名称")
    distributions: List[LevelDistribution] = Field(..., description="段位分布列表")
    
class GradeLevelBenchmark(BaseModel):
    """年级段位基准线"""
    level: ScoreLevel = Field(..., description="段位类型")
    average_percentage: float = Field(..., description="年级平均占比")

class ClassProgressIndex(BaseModel):
    """班级进步指数"""
    class_id: int = Field(..., description="班级ID")
    class_name: str = Field(..., description="班级名称")
    progress_index: float = Field(..., description="进步指数")
    rank: int = Field(..., description="进步排名")
    level_changes: Dict[ScoreLevel, float] = Field(..., description="各段位变化率")

class EnhancedStudentTrendData(StudentTrendData):
    """增强的学生趋势数据，包含排名信息"""
    grade_ranks: Dict[str, GradeRankData] = Field(default_factory=dict, description="各科目年级排名")
    dual_rank: DualRankData = Field(..., description="总分双维度排名")
    rank_history: List[RankHistory] = Field(default_factory=list, description="排名历史记录")

class LevelComparisonData(BaseModel):
    """段位分布对比数据"""
    class_distributions: List[ClassLevelDistribution] = Field(..., description="各班级段位分布")
    grade_benchmarks: List[GradeLevelBenchmark] = Field(..., description="年级段位基准线")
    class_progress: List[ClassProgressIndex] = Field(..., description="班级进步指数") 