from typing import Any, Dict, Optional, Union

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.crud.base import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, *, email: str) -> Optional[User]:
        """
        通过邮箱获取用户
        """
        return await User.get_or_none(email=email)
        
    async def get_by_username(self, *, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        """
        return await User.get_or_none(username=username)

    async def create(self, *, obj_in: UserCreate) -> User:
        """
        创建新用户
        """
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            phone=obj_in.phone,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser
        )
        await db_obj.save()
        return db_obj

    async def update(
        self, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        更新用户
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        return await super().update(db_obj=db_obj, obj_in=update_data)

    async def authenticate(self, *, username: str, password: str) -> Optional[User]:
        """
        通过用户名认证用户
        """
        user = await self.get_by_username(username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
        
    async def authenticate_email(self, *, email: str, password: str) -> Optional[User]:
        """
        通过邮箱认证用户
        """
        user = await self.get_by_email(email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """
        判断用户是否激活
        """
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        """
        判断用户是否是超级用户
        """
        return user.is_superuser


user = CRUDUser(User) 