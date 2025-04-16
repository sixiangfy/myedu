from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime
from enum import Enum

from app.models.base import BaseModel
from app.models.user import User

class AnalysisTaskStatus(str, Enum):
    """分析任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisTask(BaseModel):
    """分析任务模型"""
    task_type = fields.CharField(max_length=30, description="分析任务类型")
    user = fields.ForeignKeyField("models.User", related_name="analysis_tasks", description="创建者")
    status = fields.CharField(max_length=20, default="pending", description="任务状态")
    progress = fields.IntField(default=0, description="任务进度(百分比)")
    parameters = fields.JSONField(description="任务参数")
    completed_at = fields.DatetimeField(null=True, description="完成时间")
    results = fields.JSONField(null=True, description="分析结果")
    
    class Meta:
        table = "analysis_tasks"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"分析任务 #{self.id} ({self.task_type})"
        
    @property
    def status_enum(self) -> AnalysisTaskStatus:
        """获取状态枚举对象，方便业务逻辑使用"""
        return AnalysisTaskStatus(self.status)
        
    def set_status(self, status: AnalysisTaskStatus) -> None:
        """设置状态，接受枚举对象但存储字符串值"""
        self.status = status.value if isinstance(status, AnalysisTaskStatus) else status

class AnalysisReport(BaseModel):
    """分析报告模型"""
    task = fields.ForeignKeyField("models.AnalysisTask", related_name="reports", description="关联任务")
    report_type = fields.CharField(max_length=30, description="报告类型")
    title = fields.CharField(max_length=100, description="报告标题")
    format = fields.CharField(max_length=10, description="报告格式")
    file_path = fields.CharField(max_length=255, description="文件路径")
    size = fields.IntField(description="文件大小(字节)")
    is_public = fields.BooleanField(default=False, description="是否公开")
    
    class Meta:
        table = "analysis_reports"
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.title

# 模型快照，用于存储历史分析数据点
class AnalysisSnapshot(BaseModel):
    """分析数据快照"""
    snapshot_type = fields.CharField(max_length=30, description="快照类型")
    target_id = fields.IntField(description="目标ID(学生/班级/年级)")
    target_type = fields.CharField(max_length=20, description="目标类型")
    data = fields.JSONField(description="快照数据")
    exam_id = fields.IntField(null=True, description="关联考试ID")
    subject_id = fields.IntField(null=True, description="关联学科ID")
    
    class Meta:
        table = "analysis_snapshots"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.snapshot_type}快照 #{self.id}"

# 为Pydantic模型创建
AnalysisTask_Pydantic = pydantic_model_creator(AnalysisTask, name="AnalysisTask")
AnalysisReport_Pydantic = pydantic_model_creator(AnalysisReport, name="AnalysisReport")
AnalysisSnapshot_Pydantic = pydantic_model_creator(AnalysisSnapshot, name="AnalysisSnapshot") 