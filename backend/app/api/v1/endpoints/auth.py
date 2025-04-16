from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.crud.crud_user import user as crud_user
from app.schemas.token import Token, RefreshToken, TokenResponse
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
from app.schemas.common import StandardResponse
from jose import jwt, JWTError

router = APIRouter()


@router.post("/login", response_model=Token, summary="用户登录")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    获取登录令牌（访问令牌 + 刷新令牌）
    
    权限要求：
    - 无需特殊权限，任何用户均可访问
    """
    user = await crud_user.authenticate(
        username=form_data.username, 
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="用户未激活"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    # 创建刷新令牌
    refresh_token_expires = timedelta(days=30)  # 刷新令牌30天有效
    refresh_token = create_refresh_token(
        subject=user.id, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=TokenResponse, summary="刷新访问令牌")
async def refresh_access_token(refresh_token_data: RefreshToken) -> Any:
    """
    使用刷新令牌获取新的访问令牌
    
    权限要求：
    - 无需特殊权限，任何拥有有效刷新令牌的用户均可访问
    """
    try:
        # 验证刷新令牌
        payload = jwt.decode(
            refresh_token_data.refresh_token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 验证令牌类型
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )
        
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )
            
        # 验证用户存在且处于活动状态
        user = await crud_user.get(id=user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或未激活",
            )
            
        # 创建新的访问令牌和刷新令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.id, expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=30)
        new_refresh_token = create_refresh_token(
            subject=user.id, expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        ) 