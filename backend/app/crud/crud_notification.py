from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationUpdate


async def get_user_notifications(
    user_id: int, 
    *, 
    skip: int = 0, 
    limit: int = 100,
    is_read: Optional[bool] = None,
    type_filter: Optional[str] = None,
    include_all: bool = True  # 是否包含全员通知
) -> List[Notification]:
    """获取用户的通知"""
    query = Notification.filter(
        is_deleted=False,
    )
    
    # 过滤接收者
    if include_all:
        query = query.filter(
            (Notification.recipient_id == user_id) | (Notification.recipient_id == None)
        )
    else:
        query = query.filter(recipient_id=user_id)
    
    # 过滤过期时间
    query = query.filter(
        (Notification.expire_at == None) | (Notification.expire_at > datetime.now())
    )
    
    # 应用过滤条件
    if is_read is not None:
        query = query.filter(is_read=is_read)
    if type_filter:
        query = query.filter(type=type_filter)
        
    # 按创建时间降序排序
    return await query.order_by('-created_at').offset(skip).limit(limit).all()


async def count_user_notifications(
    user_id: int, 
    *, 
    is_read: Optional[bool] = None,
    type_filter: Optional[str] = None,
    include_all: bool = True
) -> int:
    """计算用户通知数量"""
    query = Notification.filter(
        is_deleted=False,
    )
    
    # 过滤接收者
    if include_all:
        query = query.filter(
            (Notification.recipient_id == user_id) | (Notification.recipient_id == None)
        )
    else:
        query = query.filter(recipient_id=user_id)
    
    # 过滤过期时间
    query = query.filter(
        (Notification.expire_at == None) | (Notification.expire_at > datetime.now())
    )
    
    # 应用过滤条件
    if is_read is not None:
        query = query.filter(is_read=is_read)
    if type_filter:
        query = query.filter(type=type_filter)
        
    return await query.count()


async def mark_as_read(notification_id: int, user_id: int) -> Optional[Notification]:
    """将通知标记为已读"""
    notification = await Notification.filter(
        id=notification_id,
        is_deleted=False
    ).filter(
        (Notification.recipient_id == user_id) | (Notification.recipient_id == None)
    ).first()
    
    if notification:
        notification.is_read = True
        await notification.save()
    
    return notification


async def mark_all_as_read(user_id: int) -> int:
    """将用户所有通知标记为已读，返回更新的记录数"""
    # 使用批量更新
    count = await Notification.filter(
        (Notification.recipient_id == user_id) | (Notification.recipient_id == None),
        is_read=False,
        is_deleted=False
    ).update(is_read=True)
    
    return count


async def delete_notification(notification_id: int, user_id: int) -> Optional[Notification]:
    """删除通知（软删除）"""
    notification = await Notification.filter(
        id=notification_id,
        recipient_id=user_id,
        is_deleted=False
    ).first()
    
    if notification:
        notification.is_deleted = True
        await notification.save()
    
    return notification


async def create_notification(obj_in: NotificationCreate) -> Notification:
    """创建通知"""
    notification_data = obj_in.dict()
    notification = await Notification.create(**notification_data)
    return notification


async def create_system_notification(
    title: str,
    content: str,
    level: str = "info",
    sender_id: Optional[int] = None
) -> Notification:
    """创建系统通知（发送给所有用户）"""
    return await Notification.create(
        title=title,
        content=content,
        type="system",
        level=level,
        sender_id=sender_id,
        recipient_id=None  # 表示发送给所有用户
    )


async def get_notification_with_details(notification_id: int) -> Optional[Dict]:
    """获取带详细信息的通知"""
    notification = await Notification.filter(
        id=notification_id,
        is_deleted=False
    ).prefetch_related('sender', 'recipient').first()
    
    if not notification:
        return None
        
    # 构建响应数据
    result = {
        "id": notification.id,
        "title": notification.title,
        "content": notification.content,
        "type": notification.type,
        "level": notification.level,
        "sender_id": notification.sender_id,
        "recipient_id": notification.recipient_id,
        "is_read": notification.is_read,
        "is_deleted": notification.is_deleted,
        "created_at": notification.created_at,
        "expire_at": notification.expire_at,
        "sender_name": notification.sender.username if notification.sender else None,
        "recipient_name": notification.recipient.username if notification.recipient else None
    }
    
    return result


async def get_user_notifications_with_details(
    user_id: int, 
    *, 
    skip: int = 0, 
    limit: int = 100,
    is_read: Optional[bool] = None,
    type_filter: Optional[str] = None,
    include_all: bool = True
) -> List[Dict]:
    """获取带详细信息的用户通知列表"""
    query = Notification.filter(
        is_deleted=False,
    )
    
    # 过滤接收者
    if include_all:
        query = query.filter(
            (Notification.recipient_id == user_id) | (Notification.recipient_id == None)
        )
    else:
        query = query.filter(recipient_id=user_id)
    
    # 过滤过期时间
    query = query.filter(
        (Notification.expire_at == None) | (Notification.expire_at > datetime.now())
    )
    
    # 应用过滤条件
    if is_read is not None:
        query = query.filter(is_read=is_read)
    if type_filter:
        query = query.filter(type=type_filter)
    
    # 预先加载发送者和接收者
    notifications = await query.prefetch_related(
        'sender', 'recipient'
    ).order_by('-created_at').offset(skip).limit(limit)
    
    # 构建响应数据
    results = []
    for notification in notifications:
        results.append({
            "id": notification.id,
            "title": notification.title,
            "content": notification.content,
            "type": notification.type,
            "level": notification.level,
            "sender_id": notification.sender_id,
            "recipient_id": notification.recipient_id,
            "is_read": notification.is_read,
            "is_deleted": notification.is_deleted,
            "created_at": notification.created_at,
            "expire_at": notification.expire_at,
            "sender_name": notification.sender.username if notification.sender else None,
            "recipient_name": notification.recipient.username if notification.recipient else None
        })
    
    return results


async def update_notification(notification_id: int, obj_in: NotificationUpdate) -> Optional[Notification]:
    """更新通知"""
    notification = await Notification.filter(id=notification_id).first()
    if not notification:
        return None
        
    update_data = obj_in.dict(exclude_unset=True)
    
    # 防止修改系统设置标志
    if notification.type == "system" and "type" in update_data:
        update_data.pop("type")
    
    # 更新通知
    for field, value in update_data.items():
        setattr(notification, field, value)
    
    await notification.save()
    return notification 