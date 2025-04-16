from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from tortoise.models import Model

ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD 基础类，提供基本的数据库操作
        
        :param model: Tortoise-ORM 模型类
        """
        self.model = model

    async def get(self, id: Any) -> Optional[ModelType]:
        """
        通过ID获取对象
        """
        return await self.model.get_or_none(id=id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        获取多个对象，支持分页
        """
        return await self.model.all().offset(skip).limit(limit)

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        创建新对象
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        await db_obj.save()
        return db_obj

    async def update(self, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        更新对象
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])
        
        await db_obj.save()
        return db_obj

    async def remove(self, *, id: int) -> ModelType:
        """
        删除对象
        """
        obj = await self.model.get(id=id)
        await obj.delete()
        return obj 