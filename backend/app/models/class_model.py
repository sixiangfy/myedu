from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel
from app.models.grade import Grade

class Class(BaseModel):
    """班级模型"""
    name = fields.CharField(max_length=50)  # 班级名称，如"一班"、"二班"
    code = fields.CharField(max_length=20, unique=True)  # 班级代码，如"C101"
    capacity = fields.IntField(default=0)  # 班级容量
    
    # 外键关系
    grade = fields.ForeignKeyField("models.Grade", related_name="classes")
    headteacher = fields.ForeignKeyField("models.Teacher", related_name="managed_class", null=True)
    
    # 反向关系
    students = fields.ReverseRelation["Student"]
    teachers = fields.ManyToManyField("models.Teacher", related_name="teaching_classes")
    
    class Meta:
        table = "classes"
    
    def __str__(self):
        return f"{self.grade.name}{self.name}"

# 创建Pydantic模型
Class_Pydantic = pydantic_model_creator(Class, name="Class")
ClassIn_Pydantic = pydantic_model_creator(
    Class, 
    name="ClassIn", 
    exclude_readonly=True, 
    exclude=["created_at", "updated_at"]
) 