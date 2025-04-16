from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.score import Score

class ScoreBase(BaseModel):
    """成绩基础模型"""
    score: float = Field(..., ge=0.0, le=150.0, description="成绩分数")
    ranking: Optional[int] = Field(None, gt=0, description="排名")
    comments: Optional[str] = Field(None, description="评语")
    
    @field_validator('score')
    def score_must_be_valid(cls, v):
        if v < 0:
            raise ValueError('成绩不能为负数')
        return v

class ScoreCreate(ScoreBase):
    """创建成绩模型"""
    student_id: int = Field(..., description="学生ID")
    subject_id: int = Field(..., description="学科ID")
    exam_id: int = Field(..., description="考试ID")

class ScoreUpdate(BaseModel):
    """更新成绩模型"""
    score: Optional[float] = Field(None, ge=0.0, le=150.0, description="成绩分数")
    ranking: Optional[int] = Field(None, gt=0, description="排名")
    comments: Optional[str] = Field(None, description="评语")
    
    @field_validator('score')
    def score_must_be_valid(cls, v):
        if v is not None and v < 0:
            raise ValueError('成绩不能为负数')
        return v
    
class ScoreInExam(ScoreBase):
    """考试中的成绩模型"""
    student_name: str
    subject_name: str
    
    class Config:
        from_attributes = True
        populate_by_name = True

class StudentScoreResponse(BaseModel):
    """学生成绩响应模型"""
    student_id: int
    student_name: str
    student_code: str
    scores: List[dict]
    average_score: float
    total_score: float
    score_count: int
    
    class Config:
        from_attributes = True
        populate_by_name = True

# 从模型创建Pydantic模型
Score_Pydantic = pydantic_model_creator(Score, name="Score") 