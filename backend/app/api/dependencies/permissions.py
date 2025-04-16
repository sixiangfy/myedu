from typing import List, Optional, Callable, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime

from app.api.dependencies.auth import get_current_active_user
from app.models.enums import UserRole
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.class_model import Class

# 权限错误消息
PERMISSION_ERROR_MESSAGE = "对不起，您没有权限执行此操作"

# --------------------- 角色验证依赖 ---------------------

async def check_is_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """验证用户是否为管理员"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

async def check_is_teacher_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """验证用户是否为教师或管理员"""
    if current_user.role != UserRole.TEACHER and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教师或管理员权限"
        )
    return current_user

async def check_is_headteacher_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """验证用户是否为班主任或管理员"""
    if current_user.role != UserRole.HEADTEACHER and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要班主任或管理员权限"
        )
    return current_user

# --------------------- 资源访问控制依赖 ---------------------

async def check_student_access(
    student_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """检查用户是否有权限访问学生数据"""
    # 管理员可以访问所有学生数据
    if current_user.role == UserRole.ADMIN:
        return True
        
    # 如果当前用户是学生，只能访问自己的数据
    if current_user.role == UserRole.STUDENT:
        student = await Student.get_or_none(user_id=current_user.id)
        if not student or student.id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己的数据"
            )
        return True
        
    # 如果当前用户是班主任，只能访问自己班级的学生数据
    if current_user.role == UserRole.HEADTEACHER:
        # 获取班主任对应的教师信息
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 获取班主任管理的班级
        class_obj = await Class.filter(headteacher_id=teacher.id).first()
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是任何班级的班主任"
            )
            
        # 检查学生是否属于班主任的班级
        student = await Student.get_or_none(id=student_id)
        if not student or student.class_field_id != class_obj.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己班级的学生数据"
            )
        return True
        
    # 如果当前用户是教师，检查是否教授该学生
    if current_user.role == UserRole.TEACHER:
        # 获取教师信息
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 检查学生是否在教师任教的班级中
        student = await Student.get_or_none(id=student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{student_id}的学生"
            )
            
        # 这里需要根据实际系统设计检查教师是否教授该学生所在班级
        # 简化逻辑：假设教师表中有字段表示任教班级
        # 实际情况可能需要查询教师任教班级的关系表
        teacher_classes = await Class.filter(teachers__id=teacher.id)
        if not any(cls.id == student.class_field_id for cls in teacher_classes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己任教班级的学生数据"
            )
        return True
        
    # 默认拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=PERMISSION_ERROR_MESSAGE
    )

async def check_class_access(
    class_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """检查用户是否有权限访问班级数据"""
    # 管理员可以访问所有班级数据
    if current_user.role == UserRole.ADMIN:
        return True
        
    # 如果当前用户是学生，只能访问自己所在的班级
    if current_user.role == UserRole.STUDENT:
        student = await Student.get_or_none(user_id=current_user.id)
        if not student or student.class_field_id != class_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己所在班级的数据"
            )
        return True
        
    # 如果当前用户是班主任，只能访问自己管理的班级
    if current_user.role == UserRole.HEADTEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 获取班主任管理的班级
        class_obj = await Class.filter(headteacher_id=teacher.id).first()
        if not class_obj or class_obj.id != class_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己管理的班级数据"
            )
        return True
        
    # 如果当前用户是教师，检查是否任教该班级
    if current_user.role == UserRole.TEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 检查教师是否任教该班级
        teacher_classes = await Class.filter(teachers__id=teacher.id)
        if not any(cls.id == class_id for cls in teacher_classes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己任教的班级数据"
            )
        return True
        
    # 默认拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=PERMISSION_ERROR_MESSAGE
    )

async def check_score_access(
    score_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """检查用户是否有权限访问或修改成绩数据"""
    from app.models.score import Score
    
    # 管理员可以访问所有成绩数据
    if current_user.role == UserRole.ADMIN:
        return True
        
    # 获取成绩信息
    score = await Score.get_or_none(id=score_id).prefetch_related("student", "subject")
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到ID为{score_id}的成绩"
        )
        
    # 如果当前用户是学生，只能查看自己的成绩
    if current_user.role == UserRole.STUDENT:
        student = await Student.get_or_none(user_id=current_user.id)
        if not student or student.id != score.student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己的成绩"
            )
        return True
        
    # 如果当前用户是班主任，只能查看自己班级学生的成绩
    if current_user.role == UserRole.HEADTEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 获取班主任管理的班级
        class_obj = await Class.filter(headteacher_id=teacher.id).first()
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是任何班级的班主任"
            )
            
        # 检查学生是否属于班主任的班级
        student = await Student.get_or_none(id=score.student_id)
        if not student or student.class_field_id != class_obj.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能查看自己班级学生的成绩"
            )
        return True
        
    # 如果当前用户是教师，检查是否任教该学生班级的对应科目
    if current_user.role == UserRole.TEACHER:
        teacher = await Teacher.get_or_none(user_id=current_user.id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未找到对应的教师信息"
            )
            
        # 检查教师是否教授该学科
        if teacher.subject_id != score.subject_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能管理自己任教学科的成绩"
            )
            
        # 检查学生是否在教师任教的班级中
        student = await Student.get_or_none(id=score.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{score.student_id}的学生"
            )
            
        # 检查教师是否任教该班级
        teacher_classes = await Class.filter(teachers__id=teacher.id)
        if not any(cls.id == student.class_field_id for cls in teacher_classes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您只能管理自己任教班级学生的成绩"
            )
        return True
        
    # 默认拒绝访问
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=PERMISSION_ERROR_MESSAGE
    )

# --------------------- 异常处理 ---------------------

def handle_permission_exception(exc: HTTPException) -> dict:
    """处理权限异常"""
    return {
        "code": exc.status_code,
        "message": exc.detail,
        "errors": [
            {
                "code": "PERMISSION_DENIED",
                "message": exc.detail
            }
        ],
        "timestamp": datetime.now().isoformat()
    } 