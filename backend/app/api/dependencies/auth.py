from typing import Optional, List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError, BaseModel

from app.core.config import settings
from app.models.user import User
from app.models.enums import UserRole
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.class_model import Class
from app.core.security import verify_password
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 权限异常
class PermissionDenied(HTTPException):
    def __init__(self, detail: str = "权限不足"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

# 用户不存在异常
class UserNotFound(HTTPException):
    def __init__(self, detail: str = "用户不存在或已被禁用"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

# Token无效异常
class InvalidToken(HTTPException):
    def __init__(self, detail: str = "凭证无效或已过期"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

# 获取当前用户
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    从token获取当前用户
    
    Args:
        token: JWT令牌
        
    Returns:
        User: 用户对象
        
    Raises:
        InvalidToken: 令牌无效
        UserNotFound: 用户不存在
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise InvalidToken("无法识别用户身份")
    except JWTError:
        raise InvalidToken()
        
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise UserNotFound()
        
    return user

# 获取当前激活的用户
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    获取当前激活的用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 激活的用户对象
        
    Raises:
        UserNotFound: 用户未激活
    """
    if not current_user.is_active:
        raise UserNotFound("用户未激活")
    return current_user

# 管理员权限验证依赖
async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    验证当前用户是否为管理员
    
    Args:
        current_user: 当前用户
        
    Returns:
        User: 具有管理员权限的用户
        
    Raises:
        PermissionDenied: 不是管理员
    """
    if current_user.role != UserRole.ADMIN:
        raise PermissionDenied("此操作需要管理员权限")
    return current_user

# 教师权限验证依赖
async def get_teacher_user(current_user: User = Depends(get_current_active_user)) -> tuple[User, Teacher]:
    """
    验证当前用户是否为教师
    
    Args:
        current_user: 当前用户
        
    Returns:
        tuple[User, Teacher]: 用户对象和教师对象
        
    Raises:
        PermissionDenied: 用户不是教师
    """
    if current_user.role != UserRole.TEACHER and current_user.role != UserRole.ADMIN:
        raise PermissionDenied("此操作需要教师权限")
        
    # 如果是管理员，可以直接通过权限检查
    if current_user.role == UserRole.ADMIN:
        return current_user, None
        
    # 获取教师信息
    teacher = await Teacher.get_or_none(user_id=current_user.id)
    if not teacher:
        raise PermissionDenied("教师信息不存在")
        
    return current_user, teacher

# 验证教师对班级的管理权限
async def check_teacher_class_permission(class_id: int, teacher: Teacher) -> Class:
    """
    验证教师是否有权限管理指定班级
    
    Args:
        class_id: 班级ID
        teacher: 教师对象
        
    Returns:
        Class: 班级对象
        
    Raises:
        PermissionDenied: 没有权限管理该班级
        HTTPException: 班级不存在
    """
    # 获取班级信息
    class_obj = await Class.get_or_none(id=class_id)
    if not class_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{class_id}的班级不存在"
        )
    
    # TODO: 实现教师与班级的关联关系检查
    # 这里需要根据实际业务逻辑来实现，可能的方案：
    # 1. 检查教师是否是该班级的班主任
    # 2. 检查教师是否教授该班级的课程
    # 暂时默认教师可以管理所有班级，后续可根据需求完善
    
    return class_obj

# 学生权限验证依赖
async def get_student_user(current_user: User = Depends(get_current_active_user)) -> tuple[User, Student]:
    """
    验证当前用户是否为学生
    
    Args:
        current_user: 当前用户
        
    Returns:
        tuple[User, Student]: 用户对象和学生对象
        
    Raises:
        PermissionDenied: 用户不是学生
    """
    # 管理员和教师具有学生的所有权限
    if current_user.role == UserRole.ADMIN:
        return current_user, None
        
    if current_user.role == UserRole.TEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise PermissionDenied("教师信息不存在")
        return current_user, None
        
    if current_user.role != UserRole.STUDENT:
        raise PermissionDenied("此操作需要学生权限")
        
    # 获取学生信息
    student = await Student.get_or_none(user_id=current_user.id)
    if not student:
        raise PermissionDenied("学生信息不存在")
        
    return current_user, student

# 验证学生对成绩的访问权限
async def check_student_score_permission(student_id: int, current_user: User, current_student: Optional[Student]) -> Student:
    """
    验证用户是否有权限访问指定学生的成绩
    
    Args:
        student_id: 学生ID
        current_user: 当前用户
        current_student: 当前学生对象
        
    Returns:
        Student: 学生对象
        
    Raises:
        PermissionDenied: 没有权限访问该学生成绩
        HTTPException: 学生不存在
    """
    # 管理员可以访问任何学生的成绩
    if current_user.role == UserRole.ADMIN:
        student = await Student.get_or_none(id=student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ID为{student_id}的学生不存在"
            )
        return student
        
    # 教师只能访问他任教班级学生的成绩
    if current_user.role == UserRole.TEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise PermissionDenied("教师信息不存在")
            
        student = await Student.get_or_none(id=student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ID为{student_id}的学生不存在"
            )
            
        # TODO: 实现教师与学生关联关系的检查
        # 这里需要根据实际业务逻辑实现，暂时默认教师可以访问所有学生成绩
        
        return student
        
    # 学生只能访问自己的成绩
    if current_student and student_id != current_student.id:
        raise PermissionDenied("只能查看自己的成绩")
        
    return current_student 