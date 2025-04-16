from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import check_is_admin
from app.models.enums import UserRole
from app.models.user import User
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.score import Score
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

@router.post("/", response_model=StandardResponse, summary="创建学科")
async def create_subject(
    name: str,
    code: str,
    credit: float = 0,
    description: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    创建学科
    
    - **name**: 学科名称
    - **code**: 学科代码
    - **credit**: 学分（可选，默认0）
    - **description**: 学科描述（可选）
    
    权限要求：
    - 管理员：可创建任何学科
    - 班主任/教师/学生：无权创建学科
    """
    try:
        # 检查学科代码是否已存在
        existing_subject = await Subject.get_or_none(code=code)
        if existing_subject:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"学科代码'{code}'已存在"
            )
        
        # 创建学科
        subject = await Subject.create(
            name=name,
            code=code,
            credit=credit,
            description=description
        )
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="学科创建成功",
            data=subject,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建学科失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取学科列表")
async def get_subjects(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学科列表
    
    - **search**: 搜索关键词（可选）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看与自己课程相关的学科
    - 教师：可查看自己任教的学科
    - 班主任：可查看自己任教的学科和管理班级的相关学科
    - 管理员：可查看所有学科
    """
    try:
        # 构建查询
        query = Subject.all()
        
        if search:
            query = query.filter(name__icontains=search) | query.filter(code__icontains=search)
        
        # 根据用户角色筛选
        if current_user.role == UserRole.TEACHER or current_user.role == UserRole.HEADTEACHER:
            # 教师只能看到自己任教的学科
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if teacher and teacher.subject_id:
                query = query.filter(id=teacher.subject_id)
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        subjects = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 创建响应数据
        response_data = {
            "items": subjects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学科列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取学科列表失败: {str(e)}"
        )

@router.get("/{subject_id}", response_model=StandardResponse, summary="获取学科详情")
async def get_subject(
    subject_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学科详情
    
    - **subject_id**: 学科ID
    
    权限要求：
    - 学生：可查看与自己课程相关的学科详情
    - 教师：可查看自己任教的学科详情
    - 班主任：可查看自己任教的学科和管理班级的相关学科详情
    - 管理员：可查看任何学科详情
    """
    try:
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的学科"
            )
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学科详情成功",
            data=subject,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取学科详情失败: {str(e)}"
        )

@router.put("/{subject_id}", response_model=StandardResponse, summary="更新学科信息")
async def update_subject(
    subject_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    credit: Optional[float] = None,
    description: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    更新学科信息
    
    - **subject_id**: 学科ID
    - **name**: 学科名称（可选）
    - **code**: 学科代码（可选）
    - **credit**: 学分（可选）
    - **description**: 学科描述（可选）
    
    权限要求：
    - 管理员：可更新任何学科信息
    - 班主任/教师/学生：无权更新学科信息
    """
    try:
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的学科"
            )
        
        # 检查学科代码是否重复
        if code and code != subject.code:
            existing_subject = await Subject.get_or_none(code=code)
            if existing_subject:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    f"学科代码'{code}'已存在"
                )
        
        # 更新字段
        if name:
            subject.name = name
        if code:
            subject.code = code
        if credit is not None:
            subject.credit = credit
        if description is not None:  # 允许设置为空字符串
            subject.description = description
        
        await subject.save()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="学科信息更新成功",
            data=subject,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新学科信息失败: {str(e)}"
        )

@router.delete("/{subject_id}", response_model=StandardResponse, summary="删除学科")
async def delete_subject(
    subject_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    删除学科
    
    - **subject_id**: 学科ID
    
    权限要求：
    - 管理员：可删除不被教师关联且不存在成绩记录的学科
    - 班主任/教师/学生：无权删除学科
    """
    try:
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的学科"
            )
        
        # 检查是否有教师关联到这个学科
        teacher_count = await Teacher.filter(subject_id=subject_id).count()
        if teacher_count > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除学科，该学科下有{teacher_count}名教师"
            )
        
        # 检查是否有成绩关联到这个学科
        score_count = await Score.filter(subject_id=subject_id).count()
        if score_count > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除学科，该学科下有{score_count}条成绩记录"
            )
        
        # 删除学科
        await subject.delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="学科删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除学科失败: {str(e)}"
        ) 