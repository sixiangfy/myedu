from tortoise import fields, models
from datetime import datetime

class BaseModel(models.Model):
    """基础模型类"""
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True 