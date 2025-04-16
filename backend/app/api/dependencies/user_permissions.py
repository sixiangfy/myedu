from typing import Optional
from fastapi import Depends, HTTPException, status
from datetime import datetime

from app.api.dependencies.auth import get_current_active_user
from app.models.enums import UserRole
from app.models.user import User
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.class_model import Class

# 用户管理权限错误消息
USER_PERMISSION_ERROR = "您没有权限管理用户"

async def check_user_management_permission(current_user: User = Depends(get_current_active_user)) -> User:
    """检查用户是否有权限管理用户
    
    只有管理员可以管理所有用户，班主任可以管理其班级的学生账号
    """
    if current_user.role == UserRole.ADMIN:
        return current_user
        
    if current_user.role == UserRole.HEADTEACHER:
        # 班主任仅能管理其班级的学生账号，不能创建教师账号
        return current_user
        
    # 其他角色不能管理用户
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=USER_PERMISSION_ERROR
    )
    
async def check_user_access(user_id: int, current_user: User = Depends(get_current_active_user)) -> bool:
    """检查当前用户是否有权限访问指定用户的信息
    
    返回：
    - 如果有访问权限，返回True
    - 如果没有访问权限，抛出403异常
    """
    # 用户可以访问自己的信息
    if current_user.id == user_id:
        return True
        
    # 管理员可以访问所有用户的信息
    if current_user.role == UserRole.ADMIN:
        return True
        
    # 查询目标用户
    target_user = await User.get_or_none(id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为{user_id}的用户"
        )
    
    # 班主任可以访问其班级学生的信息
    if current_user.role == UserRole.HEADTEACHER:
        # 获取班主任信息
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 如果目标用户是学生
        if target_user.role == UserRole.STUDENT:
            # 获取学生信息
            student = await Student.get_or_none(user_id=target_user.id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="未找到对应的学生信息"
                )
                
            # 获取班主任管理的班级
            class_obj = await Class.filter(headteacher_id=teacher.id).first()
            if not class_obj:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您不是任何班级的班主任"
                )
                
            # 检查学生是否在班主任管理的班级
            if student.class_field_id == class_obj.id:
                return True
    
    # 教师可以查看自己任教班级学生的基本信息
    if current_user.role == UserRole.TEACHER:
        # 如果目标用户是学生
        if target_user.role == UserRole.STUDENT:
            # 获取教师信息
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="未找到对应的教师信息"
                )
                
            # 获取学生信息
            student = await Student.get_or_none(user_id=target_user.id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="未找到对应的学生信息"
                )
                
            # 检查教师是否任教该学生所在班级
            teacher_classes = await Class.filter(teachers__id=teacher.id)
            if any(cls.id == student.class_field_id for cls in teacher_classes):
                return True
    
    # 默认拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="您没有权限访问该用户信息"
    )

async def check_user_edit_permission(user_id: int, current_user: User = Depends(get_current_active_user)) -> bool:
    """检查当前用户是否有权限编辑指定用户的信息
    
    返回：
    - 如果有编辑权限，返回True
    - 如果没有编辑权限，抛出403异常
    """
    # 用户可以编辑自己的基本信息
    if current_user.id == user_id:
        return True
        
    # 管理员可以编辑所有用户的信息
    if current_user.role == UserRole.ADMIN:
        return True
        
    # 查询目标用户
    target_user = await User.get_or_none(id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为{user_id}的用户"
        )
    
    # 班主任可以编辑其班级学生的基本信息
    if current_user.role == UserRole.HEADTEACHER:
        # 只能编辑学生用户
        if target_user.role == UserRole.STUDENT:
            # 获取班主任信息
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="未找到对应的教师信息"
                )
                
            # 获取学生信息
            student = await Student.get_or_none(user_id=target_user.id)
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="未找到对应的学生信息"
                )
                
            # 获取班主任管理的班级
            class_obj = await Class.filter(headteacher_id=teacher.id).first()
            if not class_obj:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您不是任何班级的班主任"
                )
                
            # 检查学生是否在班主任管理的班级
            if student.class_field_id == class_obj.id:
                return True
    
    # 默认拒绝编辑
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="您没有权限编辑该用户信息"
    )

async def check_role_assignment_permission(current_user: User = Depends(get_current_active_user)) -> User:
    """检查用户是否有权限分配角色
    
    只有管理员可以分配角色
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以分配用户角色"
        )
    return current_user 