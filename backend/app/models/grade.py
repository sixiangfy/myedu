from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel

class Grade(BaseModel):
    """年级模型"""
    name = fields.CharField(max_length=50, unique=True)  # 年级名称，如"一年级"、"二年级"
    code = fields.CharField(max_length=20, unique=True)  # 年级代码，如"G1"、"G2"
    description = fields.TextField(null=True)  # 年级描述
    
    # 反向关系
    classes = fields.ReverseRelation["Class"]
    
    class Meta:
        table = "grades"
    
    def __str__(self):
        return self.name

# 创建Pydantic模型
Grade_Pydantic = pydantic_model_creator(Grade, name="Grade")
GradeIn_Pydantic = pydantic_model_creator(
    Grade, 
    name="GradeIn", 
    exclude_readonly=True, 
    exclude=["created_at", "updated_at"]
) 