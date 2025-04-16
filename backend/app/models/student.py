from tortoise import fields

from app.models.base import BaseModel
from app.models.user import User
from app.models.class_model import Class

class Student(BaseModel):
    """学生模型"""
    name = fields.CharField(max_length=50)  # 学生姓名
    student_code = fields.CharField(max_length=20, unique=True)  # 学号
    gender = fields.CharField(max_length=10, null=True)  # 性别
    birth_date = fields.DateField(null=True)  # 出生日期
    address = fields.CharField(max_length=255, null=True)  # 家庭住址
    phone = fields.CharField(max_length=20, null=True)  # 联系电话
    parent_name = fields.CharField(max_length=50, null=True)  # 家长姓名
    parent_phone = fields.CharField(max_length=20, null=True)  # 家长联系电话
    
    # 外键关系
    user = fields.OneToOneField("models.User", related_name="student")
    class_field = fields.ForeignKeyField("models.Class", related_name="students", source_field="class_id")
    
    # 反向关系
    scores = fields.ReverseRelation["Score"]
    
    class Meta:
        table = "students"
    
    def __str__(self):
        return f"{self.name} ({self.student_code})"

# 直接创建标准Pydantic模型，不依赖pydantic_model_creator
from pydantic import BaseModel as PydanticBaseModel
from datetime import date, datetime
from typing import Optional

class StudentBase(PydanticBaseModel):
    name: str
    student_code: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None

    class Config:
        from_attributes = True
        
class StudentCreate(StudentBase):
    user_id: int
    class_field: int
    
class StudentUpdate(StudentBase):
    name: Optional[str] = None
    student_code: Optional[str] = None
    class_field: Optional[int] = None
    
class Student_Pydantic(StudentBase):
    id: int
    user_id: int
    class_field: int
    created_at: datetime
    updated_at: datetime
    
# 用于兼容性，保持与之前相同的命名
StudentIn_Pydantic = StudentCreate 