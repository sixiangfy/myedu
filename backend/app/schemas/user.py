from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# 共享属性
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    phone: Optional[str] = None

# 创建时需要的属性
class UserCreate(UserBase):
    email: EmailStr
    password: str

# 更新时可以修改的属性
class UserUpdate(UserBase):
    password: Optional[str] = None

# 从数据库返回的数据
class UserInDBBase(UserBase):
    id: int
    
    class Config:
        from_attributes = True

# 返回给API的用户信息
class User(UserInDBBase):
    pass

# 存储在数据库中的用户，包含哈希后的密码
class UserInDB(UserInDBBase):
    hashed_password: str 