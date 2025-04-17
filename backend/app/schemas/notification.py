from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    """通知基础Schema"""
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    type: str = Field("system", description="通知类型: system, user, class, grade")
    level: str = Field("info", description="通知级别: info, warning, error, success")
    sender_id: Optional[int] = Field(None, description="发送者ID")
    recipient_id: Optional[int] = Field(None, description="接收者ID，为空表示全员通知")
    expire_at: Optional[datetime] = Field(None, description="过期时间")


class NotificationCreate(NotificationBase):
    """创建通知Schema"""
    pass


class NotificationUpdate(BaseModel):
    """更新通知Schema"""
    title: Optional[str] = Field(None, description="通知标题")
    content: Optional[str] = Field(None, description="通知内容")
    type: Optional[str] = Field(None, description="通知类型")
    level: Optional[str] = Field(None, description="通知级别")
    is_read: Optional[bool] = Field(None, description="是否已读")
    is_deleted: Optional[bool] = Field(None, description="是否删除")
    expire_at: Optional[datetime] = Field(None, description="过期时间")


class NotificationInDB(NotificationBase):
    """数据库中的通知Schema"""
    id: int
    is_read: bool = False
    is_deleted: bool = False
    created_at: datetime

    class Config:
        orm_mode = True


class Notification(NotificationInDB):
    """响应的通知Schema"""
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    items: List[Notification]
    total: int
    unread_count: int 