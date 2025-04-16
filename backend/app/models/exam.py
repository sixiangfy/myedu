from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime

from app.models.base import BaseModel
from app.models.subject import Subject

class Exam(BaseModel):
    """考试模型"""
    name = fields.CharField(max_length=100, description="考试名称")
    description = fields.TextField(null=True, description="考试描述")
    exam_date = fields.DatetimeField(description="考试日期")
    total_score = fields.FloatField(default=100.0, description="总分值")
    
    # 外键关系
    subject = fields.ForeignKeyField("models.Subject", related_name="exams", description="关联学科")
    
    # 统一考试ID字段
    exam_id = fields.CharField(max_length=100, null=True, description="同一次考试的统一ID，用于关联不同科目的同一次考试")
    
    # 反向关系
    scores = fields.ReverseRelation["Score"]
    
    class Meta:
        table = "exams"
        ordering = ["-exam_date"]
    
    def __str__(self):
        return f"{self.name} ({self.subject.name})"

# 创建Pydantic模型
Exam_Pydantic = pydantic_model_creator(Exam, name="Exam")
ExamIn_Pydantic = pydantic_model_creator(
    Exam, 
    name="ExamIn", 
    exclude_readonly=True, 
    exclude=["created_at", "updated_at"]
) 