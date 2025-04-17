from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from app.crud import (
    get_by_id, get_by_key, get_by_keys, get_by_group, get_all_public,
    create, update, create_or_update, delete, get_multi,
    get_multi_by_filter, count_by_filter
)
from app.api.dependencies.auth import get_current_user, get_admin_user
from app.models.user import User
from app.schemas.setting import Setting, SettingCreate, SettingUpdate, SettingListResponse


router = APIRouter()


@router.get("/", response_model=SettingListResponse)
async def read_settings(
    skip: int = 0,
    limit: int = 100,
    group: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    获取系统设置列表。
    """
    settings = await get_multi_by_filter(
        skip=skip, 
        limit=limit, 
        group=group,
        is_public=is_public,
        is_system=is_system,
        search=search
    )
    total = await count_by_filter(
        group=group,
        is_public=is_public,
        is_system=is_system,
        search=search
    )
    return {"items": settings, "total": total}


@router.get("/public", response_model=List[Setting])
async def read_public_settings() -> Any:
    """
    获取所有公开的系统设置，无需登录。
    """
    return await get_all_public()


@router.get("/group/{group}", response_model=List[Setting])
async def read_settings_by_group(
    group: str = Path(..., description="设置组名"),
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取某个分组的所有设置。
    """
    return await get_by_group(group=group, is_public=is_public)


@router.get("/{key}", response_model=Setting)
async def read_setting(
    key: str = Path(..., description="设置键名"),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    获取指定键名的设置。
    """
    setting = await get_by_key(key=key)
    if not setting:
        raise HTTPException(status_code=404, detail="未找到该设置")
    
    # 如果设置不是公开的，只有管理员可以访问
    if not setting.is_public and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="没有权限访问该设置")
        
    return setting


@router.post("/", response_model=Setting)
async def create_setting(
    setting_in: SettingCreate,
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    创建系统设置。
    """
    setting = await get_by_key(key=setting_in.key)
    if setting:
        raise HTTPException(
            status_code=400,
            detail=f"键名为 '{setting_in.key}' 的设置已存在"
        )
    return await create(obj_in=setting_in)


@router.put("/{key}", response_model=Setting)
async def update_setting(
    *,
    key: str = Path(..., description="设置键名"),
    setting_in: SettingUpdate,
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    更新系统设置。
    """
    setting = await get_by_key(key=key)
    if not setting:
        raise HTTPException(status_code=404, detail="未找到该设置")
    
    # 如果是系统设置，不能修改系统设置标志
    if setting.is_system:
        return await update(id=setting.id, obj_in={
            **setting_in.dict(exclude_unset=True),
            "is_system": True  # 确保系统设置标志不被修改
        })
    
    return await update(id=setting.id, obj_in=setting_in)


@router.delete("/{key}", response_model=Setting)
async def delete_setting(
    *,
    key: str = Path(..., description="设置键名"),
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    删除系统设置。
    """
    setting = await get_by_key(key=key)
    if not setting:
        raise HTTPException(status_code=404, detail="未找到该设置")
    
    # 系统设置不允许删除
    if setting.is_system:
        raise HTTPException(status_code=400, detail="系统设置不允许删除")
    
    # 保存设置信息以便返回
    setting_copy = setting
    
    # 删除设置
    success = await delete(id=setting.id)
    if not success:
        raise HTTPException(status_code=500, detail="删除设置失败")
    
    return setting_copy


@router.post("/batch", response_model=List[Setting])
async def batch_update_settings(
    *,
    settings_in: List[SettingCreate],
    current_user: User = Depends(get_admin_user),
) -> Any:
    """
    批量创建或更新系统设置。
    """
    result = []
    for setting_in in settings_in:
        result.append(await create_or_update(obj_in=setting_in))
    return result 