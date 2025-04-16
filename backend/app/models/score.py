from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel

class Score(BaseModel):
    """成绩模型"""
    score = fields.FloatField()  # 得分
    ranking = fields.IntField(null=True)  # 排名
    comments = fields.TextField(null=True)  # 评语
    
    # 外键关系
    student = fields.ForeignKeyField("models.Student", related_name="scores")
    subject = fields.ForeignKeyField("models.Subject", related_name="scores")
    exam = fields.ForeignKeyField("models.Exam", related_name="scores")
    
    class Meta:
        table = "scores"
        unique_together = (("student", "subject", "exam"),)
    
    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.exam.name}: {self.score}"

# 创建Pydantic模型
Score_Pydantic = pydantic_model_creator(Score, name="Score")

ScoreIn_Pydantic = pydantic_model_creator(
    Score, 
    name="ScoreIn", 
    exclude_readonly=True,
    exclude=["created_at", "updated_at"]
) 