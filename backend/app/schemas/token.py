from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2兼容的访问令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class TokenPayload(BaseModel):
    """令牌载荷模型"""
    sub: Optional[int] = None
    
    
class RefreshToken(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


class TokenResponse(BaseModel):
    """完整的令牌响应模型(包含刷新令牌)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int 