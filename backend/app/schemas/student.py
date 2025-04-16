from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import date

class StudentBase(BaseModel):
    """学生基础模型"""
    name: str = Field(..., min_length=2, max_length=50, description="学生姓名")
    student_code: str = Field(..., min_length=5, max_length=20, description="学号")
    gender: Optional[str] = Field(None, description="性别")
    birth_date: Optional[date] = Field(None, description="出生日期")
    address: Optional[str] = Field(None, max_length=255, description="家庭住址")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    parent_name: Optional[str] = Field(None, max_length=50, description="家长姓名")
    parent_phone: Optional[str] = Field(None, max_length=20, description="家长联系电话")
    
    @field_validator('student_code')
    def student_code_must_be_valid(cls, v):
        if not v.isalnum():
            raise ValueError('学号只能包含字母和数字')
        return v

class StudentCreate(StudentBase):
    """创建学生模型"""
    class_field: int = Field(..., description="班级ID", alias="class_id")
    user_id: int = Field(..., description="用户ID")

class StudentUpdate(StudentBase):
    """更新学生模型"""
    name: Optional[str] = None
    student_code: Optional[str] = None
    class_field: Optional[int] = Field(None, description="班级ID", alias="class_id")

class StudentResponse(StudentBase):
    """学生响应模型"""
    id: int
    class_name: str
    grade_name: str
    
    class Config:
        from_attributes = True
        populate_by_name = True 