from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from tortoise.exceptions import DoesNotExist

from app.api.dependencies.auth import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.notification import (
    Notification, NotificationCreate, NotificationUpdate, 
    NotificationListResponse
)
from app.crud import crud_notification


router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def read_notifications(
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
    type_filter: Optional[str] = None,
    include_all: bool = True,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取当前用户的通知列表。
    """
    notifications = await crud_notification.get_user_notifications_with_details(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_read=is_read,
        type_filter=type_filter,
        include_all=include_all
    )
    
    total = await crud_notification.count_user_notifications(
        user_id=current_user.id,
        is_read=is_read,
        type_filter=type_filter,
        include_all=include_all
    )
    
    unread_count = await crud_notification.count_user_notifications(
        user_id=current_user.id,
        is_read=False,
        include_all=include_all
    )
    
    return {
        "items": notifications,
        "total": total,
        "unread_count": unread_count
    }


@router.get("/unread", response_model=NotificationListResponse)
async def read_unread_notifications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取当前用户的未读通知。
    """
    return await read_notifications(
        skip=skip,
        limit=limit,
        is_read=False,
        current_user=current_user
    )


@router.get("/count", response_model=int)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取当前用户的未读通知数量。
    """
    return await crud_notification.count_user_notifications(
        user_id=current_user.id,
        is_read=False
    )


@router.get("/{notification_id}", response_model=Notification)
async def read_notification(
    notification_id: int = Path(..., description="通知ID"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取指定通知详情。
    """
    notification = await crud_notification.get_notification_with_details(
        notification_id=notification_id
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="未找到该通知")
    
    # 检查用户是否有权限查看该通知
    if notification.get("recipient_id") and notification.get("recipient_id") != current_user.id:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="没有权限查看该通知")
    
    return notification


@router.post("/", response_model=Notification)
async def create_notification(
    notification_in: NotificationCreate,
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    创建通知（仅管理员）。
    """
    # 如果没有指定发送者，则使用当前用户
    if not notification_in.sender_id:
        notification_in.sender_id = current_user.id
    
    # 验证接收者是否存在
    if notification_in.recipient_id:
        try:
            recipient = await User.get(id=notification_in.recipient_id)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="接收者不存在")
    
    # 创建通知
    notification = await crud_notification.create_notification(obj_in=notification_in)
    
    # 获取通知详情
    return await crud_notification.get_notification_with_details(notification_id=notification.id)


@router.put("/{notification_id}/read", response_model=Notification)
async def mark_as_read(
    notification_id: int = Path(..., description="通知ID"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    将通知标记为已读。
    """
    notification = await crud_notification.mark_as_read(
        notification_id=notification_id, 
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="未找到该通知或无权限操作")
    
    return await crud_notification.get_notification_with_details(notification_id=notification.id)


@router.put("/mark-all-read", response_model=int)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    将所有通知标记为已读，返回已更新的通知数量。
    """
    return await crud_notification.mark_all_as_read(user_id=current_user.id)


@router.delete("/{notification_id}", response_model=Notification)
async def delete_notification(
    notification_id: int = Path(..., description="通知ID"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    删除通知（软删除）。
    """
    # 管理员可以删除任何通知
    if current_user.is_superuser:
        notification = await crud_notification.get_notification_with_details(notification_id=notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="未找到该通知")
            
        # 软删除通知
        deleted_notification = await crud_notification.delete_notification(
            notification_id=notification_id,
            user_id=None  # 管理员可以删除任何通知
        )
        
        return await crud_notification.get_notification_with_details(notification_id=notification_id)
    
    # 普通用户只能删除自己的通知
    notification = await crud_notification.delete_notification(
        notification_id=notification_id,
        user_id=current_user.id
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="未找到该通知或无权限删除")
    
    return await crud_notification.get_notification_with_details(notification_id=notification.id)


@router.post("/system", response_model=Notification)
async def create_system_notification(
    *,
    title: str = Body(..., description="通知标题"),
    content: str = Body(..., description="通知内容"),
    level: str = Body("info", description="通知级别: info, warning, error, success"),
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    创建系统通知（发送给所有用户）。
    """
    notification = await crud_notification.create_system_notification(
        title=title,
        content=content,
        level=level,
        sender_id=current_user.id
    )
    
    return await crud_notification.get_notification_with_details(notification_id=notification.id)


@router.post("/batch", response_model=List[Notification])
async def create_batch_notifications(
    *,
    notifications_in: List[NotificationCreate],
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    批量创建通知（仅管理员）。
    """
    results = []
    
    for notification_in in notifications_in:
        # 如果没有指定发送者，则使用当前用户
        if not notification_in.sender_id:
            notification_in.sender_id = current_user.id
        
        try:
            # 验证接收者是否存在（如果指定了接收者）
            if notification_in.recipient_id:
                try:
                    recipient = await User.get(id=notification_in.recipient_id)
                except DoesNotExist:
                    continue  # 跳过无效接收者
            
            # 创建通知
            notification = await crud_notification.create_notification(obj_in=notification_in)
            
            # 获取通知详情
            notification_detail = await crud_notification.get_notification_with_details(
                notification_id=notification.id
            )
            results.append(notification_detail)
        except Exception:
            # 记录错误但继续处理其他通知
            continue
    
    return results 