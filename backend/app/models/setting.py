from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel


class Setting(BaseModel):
    """系统设置模型"""
    key = fields.CharField(max_length=100, unique=True, index=True, description="设置键名")
    value = fields.TextField(null=True, description="设置值")
    value_type = fields.CharField(max_length=20, default="string", description="值类型: string, number, boolean, json")
    description = fields.CharField(max_length=200, null=True, description="设置描述")
    group = fields.CharField(max_length=50, null=True, index=True, description="设置分组")
    is_public = fields.BooleanField(default=False, description="是否公开(不需要登录就可查看)")
    is_system = fields.BooleanField(default=False, description="是否为系统设置(不可由用户修改)")
    order = fields.IntField(default=0, description="排序")
    
    class Meta:
        table = "settings"
    
    def __str__(self):
        return f"{self.key}: {self.value}"


# 创建Pydantic模型
Setting_Pydantic = pydantic_model_creator(Setting, name="Setting")
SettingIn_Pydantic = pydantic_model_creator(
    Setting, 
    name="SettingIn", 
    exclude_readonly=True,
    exclude=["created_at", "updated_at"]
) 