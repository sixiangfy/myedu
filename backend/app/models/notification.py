from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models.base import BaseModel


class Notification(BaseModel):
    """通知模型"""
    title = fields.CharField(max_length=200, description="通知标题")
    content = fields.TextField(description="通知内容")
    type = fields.CharField(max_length=50, default="system", description="通知类型: system, user, class, grade")
    level = fields.CharField(max_length=20, default="info", description="通知级别: info, warning, error, success")
    sender = fields.ForeignKeyField('models.User', related_name='sent_notifications', null=True, description="发送者")
    recipient = fields.ForeignKeyField('models.User', related_name='received_notifications', null=True, description="接收者，为空表示全员通知")
    is_read = fields.BooleanField(default=False, description="是否已读")
    is_deleted = fields.BooleanField(default=False, description="是否删除")
    expire_at = fields.DatetimeField(null=True, description="过期时间")
    
    class Meta:
        table = "notifications"
    
    def __str__(self):
        return f"{self.title} ({self.type})"


# 创建Pydantic模型
Notification_Pydantic = pydantic_model_creator(Notification, name="Notification")
NotificationIn_Pydantic = pydantic_model_creator(
    Notification, 
    name="NotificationIn", 
    exclude_readonly=True,
    exclude=["is_read", "is_deleted", "created_at", "updated_at"]
) 