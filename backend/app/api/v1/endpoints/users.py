from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional, Any
from datetime import datetime
from pydantic import EmailStr

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.user_permissions import (
    check_user_management_permission, 
    check_user_access, 
    check_user_edit_permission,
    check_role_assignment_permission
)
from app.core.security import get_password_hash, verify_password
from app.models.enums import UserRole
from app.models.user import User, User_Pydantic, UserIn_Pydantic
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.class_model import Class
from app.schemas.common import StandardResponse, PaginatedResponse

router = APIRouter()

# 错误处理函数
def create_error_response(status_code: int, detail: str) -> StandardResponse:
    """创建标准错误响应"""
    return StandardResponse(
        code=status_code,
        message=detail,
        data=None,
        timestamp=datetime.now()
    )

@router.get("/", response_model=StandardResponse, summary="获取用户列表")
async def get_users(
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(check_user_management_permission)
):
    """
    获取用户列表
    
    - **role**: 按角色筛选（可选）
    - **search**: 搜索关键词（用户名/邮箱）（可选）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 管理员：可查看所有用户
    - 班主任：可查看自己管理班级的学生
    - 普通教师：无权查看用户列表
    - 学生：无权查看用户列表
    """
    try:
        # 构建查询
        query = User.all()
        
        if role:
            query = query.filter(role=role)
            
        if search:
            query = query.filter(username__icontains=search) | query.filter(email__icontains=search)
            
        # 计算总数
        total = await query.count()
        
        # 分页查询
        users = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 转换为Pydantic模型
        user_data = [await User_Pydantic.from_tortoise_orm(user) for user in users]
        
        # 创建响应数据
        response_data = {
            "items": user_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取用户列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取用户列表失败: {str(e)}"
        )

@router.post("/", response_model=StandardResponse, summary="创建新用户")
async def create_user(
    user_in: UserIn_Pydantic,
    current_user: User = Depends(check_user_management_permission)
):
    """
    创建新用户
    
    - **username**: 用户名
    - **password**: 密码
    - **role**: 角色
    - **email**: 电子邮箱（可选）
    - **phone**: 电话号码（可选）
    
    权限要求：
    - 管理员：可创建任何角色的用户
    - 班主任：只能创建学生用户
    - 普通教师：无权创建用户
    - 学生：无权创建用户
    """
    try:
        # 检查用户名是否已存在
        existing_user = await User.get_or_none(username=user_in.username)
        if existing_user:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                "用户名已存在"
            )
            
        # 检查电子邮箱是否已存在
        if user_in.email:
            existing_email = await User.get_or_none(email=user_in.email)
            if existing_email:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    "电子邮箱已存在"
                )
                
        # 如果不是管理员，检查角色分配权限
        if current_user.role != UserRole.ADMIN and user_in.role not in [UserRole.STUDENT]:
            return create_error_response(
                status.HTTP_403_FORBIDDEN, 
                "您只能创建学生用户"
            )
            
        # 创建用户
        user_dict = user_in.dict(exclude_unset=True)
        user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
        user = await User.create(**user_dict)
        
        # 转换为Pydantic模型
        user_data = await User_Pydantic.from_tortoise_orm(user)
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="用户创建成功",
            data=user_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建用户失败: {str(e)}"
        )

@router.get("/{user_id}", response_model=StandardResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定用户信息
    
    - **user_id**: 用户ID
    
    权限要求：
    - 所有用户：可查看自己的信息
    - 班主任：可查看自己管理班级的学生信息
    - 管理员：可查看任何用户的信息
    """
    try:
        # 检查用户是否有权限访问该用户信息
        await check_user_access(user_id, current_user)
        
        # 获取用户信息
        user = await User.get_or_none(id=user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{user_id}的用户"
            )
            
        # 转换为Pydantic模型
        user_data = await User_Pydantic.from_tortoise_orm(user)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取用户信息成功",
            data=user_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(
            e.status_code, 
            e.detail
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取用户信息失败: {str(e)}"
        )

@router.put("/{user_id}", response_model=StandardResponse, summary="更新用户信息")
async def update_user(
    user_id: int,
    user_update: UserIn_Pydantic,
    current_user: User = Depends(get_current_active_user)
):
    """
    更新用户信息
    
    - **user_id**: 用户ID
    - **username**: 用户名（可选）
    - **password**: 密码（可选）
    - **role**: 角色（可选，需要管理员权限）
    - **email**: 电子邮箱（可选）
    - **phone**: 电话号码（可选）
    
    权限要求：
    - 所有用户：可更新自己的基本信息
    - 班主任：可更新自己管理班级学生的信息
    - 管理员：可更新任何用户的信息
    - 只有管理员可以更改用户角色
    """
    try:
        # 检查用户是否有权限编辑该用户信息
        await check_user_edit_permission(user_id, current_user)
        
        # 获取用户信息
        user = await User.get_or_none(id=user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{user_id}的用户"
            )
            
        # 处理角色更改
        if "role" in user_update.dict(exclude_unset=True):
            # 只有管理员可以更改角色
            if current_user.role != UserRole.ADMIN:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "只有管理员可以更改用户角色"
                )
        
        # 处理用户名更改
        if user_update.username and user_update.username != user.username:
            # 检查用户名是否已存在
            existing_user = await User.get_or_none(username=user_update.username)
            if existing_user:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    "用户名已存在"
                )
                
        # 处理电子邮箱更改
        if user_update.email and user_update.email != user.email:
            # 检查电子邮箱是否已存在
            existing_email = await User.get_or_none(email=user_update.email)
            if existing_email:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    "电子邮箱已存在"
                )
        
        # 更新用户信息
        user_dict = user_update.dict(exclude_unset=True)
        if "password" in user_dict:
            user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
            
        for field, value in user_dict.items():
            setattr(user, field, value)
            
        await user.save()
        
        # 转换为Pydantic模型
        user_data = await User_Pydantic.from_tortoise_orm(user)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="用户信息更新成功",
            data=user_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(
            e.status_code, 
            e.detail
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新用户信息失败: {str(e)}"
        )

@router.delete("/{user_id}", response_model=StandardResponse, summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: User = Depends(check_user_management_permission)
):
    """
    删除用户
    
    - **user_id**: 用户ID
    
    权限要求：
    - 管理员：可删除任何非管理员用户
    - 班主任：只能删除自己管理班级的学生
    - 普通教师：无权删除用户
    - 学生：无权删除用户
    """
    try:
        # 获取用户信息
        user = await User.get_or_none(id=user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{user_id}的用户"
            )
            
        # 非管理员不能删除管理员或教师
        if current_user.role != UserRole.ADMIN and user.role in [UserRole.ADMIN, UserRole.TEACHER, UserRole.HEADTEACHER]:
            return create_error_response(
                status.HTTP_403_FORBIDDEN, 
                "您没有权限删除该用户"
            )
            
        # 非管理员只能删除自己班级的学生
        if current_user.role == UserRole.HEADTEACHER and user.role == UserRole.STUDENT:
            # 获取班主任信息
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if not teacher:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "未找到对应的教师信息"
                )
                
            # 获取学生信息
            student = await Student.get_or_none(user_id=user.id)
            if not student:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    "未找到对应的学生信息"
                )
                
            # 获取班主任管理的班级
            class_obj = await Class.filter(headteacher_id=teacher.id).first()
            if not class_obj:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "您不是任何班级的班主任"
                )
                
            # 检查学生是否在班主任管理的班级
            if student.class_field_id != class_obj.id:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "您只能删除自己班级的学生用户"
                )
        
        # 删除用户
        await user.delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="用户删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除用户失败: {str(e)}"
        )

@router.post("/change-role/{user_id}", response_model=StandardResponse, summary="修改用户角色")
async def change_user_role(
    user_id: int,
    role: UserRole,
    current_user: User = Depends(check_role_assignment_permission)
):
    """
    更改用户角色（仅限管理员）
    
    - **user_id**: 用户ID
    - **role**: 新角色
    
    权限要求：
    - 管理员：可修改任何用户的角色
    - 班主任：无权修改用户角色
    - 普通教师：无权修改用户角色
    - 学生：无权修改用户角色
    """
    try:
        # 获取用户信息
        user = await User.get_or_none(id=user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{user_id}的用户"
            )
            
        # 更改用户角色
        user.role = role
        await user.save()
        
        # 转换为Pydantic模型
        user_data = await User_Pydantic.from_tortoise_orm(user)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="用户角色更改成功",
            data=user_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更改用户角色失败: {str(e)}"
        )

@router.post("/change-password", response_model=StandardResponse, summary="修改用户密码")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    修改当前用户密码
    
    - **current_password**: 当前密码
    - **new_password**: 新密码
    
    权限要求：
    - 所有已登录用户：可修改自己的密码
    """
    try:
        # 验证当前密码
        if not verify_password(current_password, current_user.hashed_password):
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                "当前密码不正确"
            )
            
        # 更改密码
        current_user.hashed_password = get_password_hash(new_password)
        await current_user.save()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="密码修改成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"修改密码失败: {str(e)}"
        )

@router.get("/me/profile", response_model=StandardResponse, summary="获取当前用户信息")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户个人资料
    
    权限要求：
    - 所有已登录用户：可获取自己的个人资料
    """
    try:
        # 转换为Pydantic模型
        user_data = await User_Pydantic.from_tortoise_orm(current_user)
        
        # 获取更多用户信息
        profile_data = {
            "user": user_data,
            "additional_info": {}
        }
        
        # 根据角色获取不同的额外信息
        if current_user.role == UserRole.STUDENT:
            student = await Student.get_or_none(user_id=current_user.id).prefetch_related("class_field")
            if student:
                profile_data["additional_info"] = {
                    "student_id": student.id,
                    "name": student.name,
                    "student_code": student.student_code,
                    "class_name": student.class_field.name if hasattr(student, "class_field") else None
                }
        
        elif current_user.role in [UserRole.TEACHER, UserRole.HEADTEACHER]:
            teacher = await Teacher.get_or_none(user_id=current_user.id).prefetch_related("subject")
            if teacher:
                profile_data["additional_info"] = {
                    "teacher_id": teacher.id,
                    "name": teacher.name,
                    "teacher_code": teacher.teacher_code,
                    "subject": teacher.subject.name if hasattr(teacher, "subject") else None
                }
                
                # 如果是班主任，获取管理的班级
                if current_user.role == UserRole.HEADTEACHER:
                    class_obj = await Class.filter(headteacher_id=teacher.id).first()
                    if class_obj:
                        profile_data["additional_info"]["managed_class"] = class_obj.name
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取个人资料成功",
            data=profile_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取个人资料失败: {str(e)}"
        ) 