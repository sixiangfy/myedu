from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel
from app.models.enums import UserRole

class User(BaseModel):
    """用户模型"""
    username = fields.CharField(max_length=50, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255)
    role = fields.CharEnumField(UserRole, default=UserRole.STUDENT)
    email = fields.CharField(max_length=255, unique=True, null=True)
    phone = fields.CharField(max_length=20, null=True)
    is_active = fields.BooleanField(default=True)
    
    # 通知关系 - 需要在导入Notification模型后再关联
    sent_notifications = fields.ReverseRelation["Notification"]
    received_notifications = fields.ReverseRelation["Notification"]
    
    class Meta:
        table = "users"
    
    def __str__(self):
        return f"{self.username} ({self.role})"

# 创建Pydantic模型
User_Pydantic = pydantic_model_creator(User, name="User", exclude=["hashed_password"])
UserIn_Pydantic = pydantic_model_creator(
    User, 
    name="UserIn", 
    exclude_readonly=True, 
    exclude=["hashed_password", "created_at", "updated_at"]
) 