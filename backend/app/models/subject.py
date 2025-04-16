from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel

class Subject(BaseModel):
    """学科模型"""
    name = fields.CharField(max_length=50, unique=True)  # 学科名称
    code = fields.CharField(max_length=20, unique=True)  # 学科代码
    description = fields.TextField(null=True)  # 学科描述
    
    # 反向关系
    teachers = fields.ReverseRelation["Teacher"]
    exams = fields.ReverseRelation["Exam"]
    scores = fields.ReverseRelation["Score"]
    
    class Meta:
        table = "subjects"
    
    def __str__(self):
        return self.name

# 创建Pydantic模型
Subject_Pydantic = pydantic_model_creator(Subject, name="Subject")
SubjectIn_Pydantic = pydantic_model_creator(
    Subject, 
    name="SubjectIn", 
    exclude_readonly=True, 
    exclude=["created_at", "updated_at"]
) 