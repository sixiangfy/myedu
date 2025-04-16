from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel
from app.models.subject import Subject
from app.models.user import User

class Teacher(BaseModel):
    """教师模型"""
    name = fields.CharField(max_length=50)  # 教师姓名
    teacher_code = fields.CharField(max_length=20, unique=True)  # 教师编号
    phone = fields.CharField(max_length=20, null=True)  # 联系电话
    email = fields.CharField(max_length=50, null=True)  # 电子邮箱
    
    # 外键关系
    user = fields.OneToOneField("models.User", related_name="teacher")
    subject = fields.ForeignKeyField("models.Subject", related_name="teachers")
    
    # 反向关系
    managed_class = fields.ReverseRelation["Class"]
    teaching_classes = fields.ManyToManyRelation["Class"]
    
    class Meta:
        table = "teachers"
    
    def __str__(self):
        return f"{self.name} ({self.subject.name})"

# 创建Pydantic模型
Teacher_Pydantic = pydantic_model_creator(Teacher, name="Teacher")
TeacherIn_Pydantic = pydantic_model_creator(
    Teacher, 
    name="TeacherIn", 
    exclude_readonly=True, 
    exclude=["created_at", "updated_at"]
) 