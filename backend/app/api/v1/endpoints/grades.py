from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import check_is_admin
from app.models.enums import UserRole
from app.models.user import User
from app.models.grade import Grade
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

@router.post("/", response_model=StandardResponse, summary="创建年级")
async def create_grade(
    name: str,
    code: str,
    description: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    创建年级
    
    - **name**: 年级名称
    - **code**: 年级代码
    - **description**: 年级描述（可选）
    
    权限要求：
    - 管理员：可创建年级
    - 教师/班主任/学生：无权创建年级
    """
    try:
        # 检查年级代码是否已存在
        existing_grade = await Grade.get_or_none(code=code)
        if existing_grade:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"年级代码'{code}'已存在"
            )
        
        # 创建年级
        grade = await Grade.create(
            name=name,
            code=code,
            description=description
        )
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="年级创建成功",
            data=grade,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建年级失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取年级列表")
async def get_grades(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取年级列表，支持分页和搜索
    
    - **search**: 搜索关键词（可选，按名称或描述搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己所在年级
    - 教师：可查看自己任教班级所在的年级
    - 班主任：可查看自己管理班级所在的年级
    - 管理员：可查看所有年级
    """
    try:
        # 构建查询
        query = Grade.all()
        
        if search:
            query = query.filter(name__icontains=search) | query.filter(code__icontains=search)
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        grades = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 创建响应数据
        response_data = {
            "items": grades,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取年级列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取年级列表失败: {str(e)}"
        )

@router.get("/{grade_id}", response_model=StandardResponse, summary="获取年级详情")
async def get_grade(
    grade_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取年级详情
    
    - **grade_id**: 年级ID
    
    权限要求：
    - 学生：可查看自己所在年级
    - 教师：可查看自己任教班级所在的年级
    - 班主任：可查看自己管理班级所在的年级
    - 管理员：可查看任何年级
    """
    try:
        grade = await Grade.get_or_none(id=grade_id)
        if not grade:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{grade_id}的年级"
            )
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取年级详情成功",
            data=grade,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取年级详情失败: {str(e)}"
        )

@router.put("/{grade_id}", response_model=StandardResponse, summary="更新年级信息")
async def update_grade(
    grade_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    更新年级信息
    
    - **grade_id**: 年级ID
    - **name**: 年级名称（可选）
    - **code**: 年级代码（可选）
    - **description**: 年级描述（可选）
    
    权限要求：
    - 管理员：可更新任何年级信息
    - 教师/班主任/学生：无权更新年级信息
    """
    try:
        grade = await Grade.get_or_none(id=grade_id)
        if not grade:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{grade_id}的年级"
            )
        
        # 检查年级代码是否重复
        if code and code != grade.code:
            existing_grade = await Grade.get_or_none(code=code)
            if existing_grade:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    f"年级代码'{code}'已存在"
                )
        
        # 更新字段
        if name:
            grade.name = name
        if code:
            grade.code = code
        if description is not None:  # 允许设置为空字符串
            grade.description = description
        
        await grade.save()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="年级信息更新成功",
            data=grade,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新年级信息失败: {str(e)}"
        )

@router.delete("/{grade_id}", response_model=StandardResponse, summary="删除年级")
async def delete_grade(
    grade_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    删除年级
    
    - **grade_id**: 年级ID
    
    权限要求：
    - 管理员：可删除不包含任何班级的年级
    - 教师/班主任/学生：无权删除年级
    """
    try:
        grade = await Grade.get_or_none(id=grade_id)
        if not grade:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{grade_id}的年级"
            )
        
        # 检查是否有关联的班级
        class_count = await grade.classes.all().count()
        if class_count > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除年级，该年级下有{class_count}个班级"
            )
        
        # 删除年级
        await grade.delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="年级删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除年级失败: {str(e)}"
        )

@router.get("/{grade_id}/classes", response_model=StandardResponse, summary="获取年级下的班级列表")
async def get_grade_classes(
    grade_id: int,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定年级下的班级列表
    
    - **grade_id**: 年级ID
    - **search**: 搜索关键词（可选，按班级名称或描述搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己所在年级的班级列表
    - 教师：可查看自己任教班级所在年级的班级列表
    - 班主任：可查看自己管理班级所在年级的班级列表
    - 管理员：可查看任何年级的班级列表
    """
    try:
        # 构建查询
        query = Grade.all()
        
        if search:
            query = query.filter(name__icontains=search) | query.filter(code__icontains=search)
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        grades = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 创建响应数据
        response_data = {
            "items": grades,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取年级下的班级列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取年级下的班级列表失败: {str(e)}"
        )

@router.get("/{grade_id}/subjects", response_model=StandardResponse, summary="获取年级下的学科列表")
async def get_grade_subjects(
    grade_id: int,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定年级下的学科列表
    
    - **grade_id**: 年级ID
    - **search**: 搜索关键词（可选，按学科名称或描述搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己所在年级的学科列表
    - 教师：可查看自己任教班级所在年级的学科列表
    - 班主任：可查看自己管理班级所在年级的学科列表
    - 管理员：可查看任何年级的学科列表
    """
    try:
        # 构建查询
        query = Grade.all()
        
        if search:
            query = query.filter(name__icontains=search) | query.filter(code__icontains=search)
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        grades = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 创建响应数据
        response_data = {
            "items": grades,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取年级下的学科列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取年级下的学科列表失败: {str(e)}"
        ) 