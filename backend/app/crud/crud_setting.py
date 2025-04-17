from typing import List, Optional, Dict, Any, Union
from tortoise.expressions import Q

from app.models.setting import Setting
from app.schemas.setting import SettingCreate, SettingUpdate


async def get_by_id(id: int) -> Optional[Setting]:
    """通过ID获取设置"""
    return await Setting.get_or_none(id=id)


async def get_by_key(key: str) -> Optional[Setting]:
    """通过key获取设置"""
    return await Setting.get_or_none(key=key)


async def get_by_keys(keys: List[str]) -> List[Setting]:
    """通过多个key获取设置"""
    return await Setting.filter(key__in=keys)


async def get_by_group(group: str, is_public: bool = None) -> List[Setting]:
    """获取某个分组的所有设置"""
    query = Setting.filter(group=group)
    if is_public is not None:
        query = query.filter(is_public=is_public)
    return await query.order_by("-order")


async def get_all_public() -> List[Setting]:
    """获取所有公开设置"""
    return await Setting.filter(is_public=True)


async def create(obj_in: Union[SettingCreate, Dict[str, Any]]) -> Setting:
    """创建设置"""
    if isinstance(obj_in, dict):
        create_data = obj_in
    else:
        create_data = obj_in.dict()
    
    return await Setting.create(**create_data)


async def update(id: int, obj_in: Union[SettingUpdate, Dict[str, Any]]) -> Optional[Setting]:
    """更新设置"""
    setting = await Setting.get_or_none(id=id)
    if not setting:
        return None
        
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.dict(exclude_unset=True)
    
    # 更新设置
    for field, value in update_data.items():
        setattr(setting, field, value)
    
    await setting.save()
    return setting


async def create_or_update(obj_in: Union[SettingCreate, Dict[str, Any]]) -> Setting:
    """创建或更新设置"""
    if isinstance(obj_in, dict):
        key = obj_in.get("key")
    else:
        key = obj_in.key

    db_obj = await get_by_key(key)
    if db_obj:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        # 更新设置
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        await db_obj.save()
        return db_obj
    else:
        return await create(obj_in)


async def delete(id: int) -> bool:
    """删除设置"""
    deleted_count = await Setting.filter(id=id).delete()
    return deleted_count > 0


async def get_multi(*, skip: int = 0, limit: int = 100) -> List[Setting]:
    """获取多条记录"""
    return await Setting.all().offset(skip).limit(limit)


async def get_multi_by_filter(
    *, 
    skip: int = 0, 
    limit: int = 100,
    group: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Setting]:
    """带过滤条件的获取多条记录"""
    query = Setting.all()
    
    # 应用过滤条件
    if group:
        query = query.filter(group=group)
    if is_public is not None:
        query = query.filter(is_public=is_public)
    if is_system is not None:
        query = query.filter(is_system=is_system)
    if search:
        query = query.filter(
            Q(key__icontains=search) | Q(description__icontains=search)
        )

    # 应用排序和分页
    return await query.order_by("group", "-order").offset(skip).limit(limit)


async def count_by_filter(
    *, 
    group: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """带过滤条件的计数"""
    query = Setting.all()
    
    # 应用过滤条件
    if group:
        query = query.filter(group=group)
    if is_public is not None:
        query = query.filter(is_public=is_public)
    if is_system is not None:
        query = query.filter(is_system=is_system)
    if search:
        query = query.filter(
            Q(key__icontains=search) | Q(description__icontains=search)
        )

    return await query.count() 