from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import check_is_admin, check_is_teacher_or_admin
from app.models.enums import UserRole
from app.models.user import User
from app.models.exam import Exam
from app.models.subject import Subject
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

@router.post("/", response_model=StandardResponse, summary="创建考试")
async def create_exam(
    name: str,
    subject_id: int,
    exam_date: datetime,
    total_score: float = 100.0,
    description: Optional[str] = None,
    exam_id: Optional[str] = None,
    current_user: User = Depends(check_is_teacher_or_admin)
):
    """
    创建考试
    
    - **name**: 考试名称
    - **subject_id**: 学科ID
    - **exam_date**: 考试日期
    - **total_score**: 总分（可选，默认100）
    - **description**: 考试描述（可选）
    - **exam_id**: 考试组ID（可选，用于关联同一次考试的不同科目）
    
    权限要求：
    - 教师：可为自己任教的学科创建考试
    - 班主任：可为自己任教的学科创建考试
    - 管理员：可创建任何学科的考试
    - 学生：无权创建考试
    """
    try:
        # 检查学科是否存在
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的学科"
            )
        
        # 如果提供了exam_id，检查是否已存在相同学科的考试
        if exam_id:
            existing_exam = await Exam.filter(exam_id=exam_id, subject_id=subject_id).first()
            if existing_exam:
                return create_error_response(
                    status.HTTP_409_CONFLICT,
                    f"考试组ID为{exam_id}中已存在{subject.name}科目的考试"
                )
            
            # 获取考试组中第一个考试的信息（如果有的话）
            first_exam = await Exam.filter(exam_id=exam_id).first()
            if first_exam:
                # 如果考试组已存在，使用相同的名称和日期以保持一致性
                name = first_exam.name
                exam_date = first_exam.exam_date
                if not description:
                    description = first_exam.description
        
        # 创建考试
        exam = await Exam.create(
            name=name,
            subject_id=subject_id,
            exam_date=exam_date,
            total_score=total_score,
            description=description,
            exam_id=exam_id
        )
        
        # 预加载关联数据以便返回
        await exam.fetch_related("subject")
        
        # 如果有考试组ID，获取所有相关科目
        related_subjects = []
        if exam_id:
            all_exams = await Exam.filter(exam_id=exam_id).prefetch_related("subject")
            for exam_obj in all_exams:
                related_subjects.append({
                    "id": exam_obj.subject.id,
                    "name": exam_obj.subject.name
                })
        else:
            related_subjects.append({
                "id": exam.subject.id,
                "name": exam.subject.name
            })
        
        exam_data = {
            "id": exam.id,
            "name": exam.name,
            "exam_date": exam.exam_date,
            "total_score": exam.total_score,
            "description": exam.description,
            "subjects": related_subjects,
            "exam_id": exam.exam_id
        }
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="考试创建成功",
            data=exam_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建考试失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取考试列表")
async def get_exams(
    subject_id: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取考试列表，支持分页和筛选
    
    - **subject_id**: 学科ID（可选，按学科筛选）
    - **search**: 搜索关键词（可选，按名称或描述搜索）
    - **start_date**: 开始日期（可选，按日期范围筛选）
    - **end_date**: 结束日期（可选，按日期范围筛选）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己参与的考试
    - 教师：可查看自己任教学科的考试
    - 班主任：可查看自己任教学科和管理班级所有学科的考试
    - 管理员：可查看所有考试
    """
    try:
        # 构建查询
        query = Exam.all().prefetch_related("subject")
        
        # 根据学科筛选
        if subject_id:
            query = query.filter(subject_id=subject_id)
        
        # 根据日期范围筛选
        if start_date:
            query = query.filter(exam_date__gte=start_date)
        if end_date:
            query = query.filter(exam_date__lte=end_date)
            
        # 搜索
        if search:
            query = query.filter(name__icontains=search) | query.filter(description__icontains=search)
        
        # 获取所有符合条件的考试
        all_exams = await query.order_by("-exam_date")
        
        # 根据exam_id将考试分组
        exam_groups = {}
        for exam in all_exams:
            group_key = exam.exam_id if exam.exam_id else f"single_{exam.id}"
            if group_key not in exam_groups:
                exam_groups[group_key] = {
                    "id": exam.id,
                    "name": exam.name,
                    "exam_date": exam.exam_date,
                    "total_score": exam.total_score,
                    "description": exam.description,
                    "subjects": [],
                }
            # 添加科目信息
            exam_groups[group_key]["subjects"].append({
                "id": exam.subject.id,
                "name": exam.subject.name
            })
        
        # 转换为列表并分页
        exam_list = list(exam_groups.values())
        exam_list.sort(key=lambda x: x["exam_date"], reverse=True)
        
        # 计算总数
        total = len(exam_list)
        
        # 应用分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_exams = exam_list[start_idx:end_idx]
        
        # 创建响应数据
        response_data = {
            "items": paginated_exams,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取考试列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取考试列表失败: {str(e)}"
        )

@router.get("/{exam_id}", response_model=StandardResponse, summary="获取考试详情")
async def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取考试详细信息
    
    - **exam_id**: 考试ID
    
    权限要求：
    - 学生：可查看自己参与的考试
    - 教师：可查看自己任教学科的考试
    - 班主任：可查看自己任教学科和管理班级所有学科的考试
    - 管理员：可查看任何考试
    """
    try:
        exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject")
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 统计参与考试的学生数量
        score_count = await exam.scores.all().count()
        
        # 获取同一个exam_id的所有考试科目
        related_subjects = []
        if exam.exam_id:
            # 查询同一考试ID下的所有科目
            related_exams = await Exam.filter(exam_id=exam.exam_id).prefetch_related("subject")
            for related_exam in related_exams:
                related_subjects.append({
                    "id": related_exam.subject.id,
                    "name": related_exam.subject.name
                })
        
        # 如果没有相关科目，则至少包含当前考试的科目
        if not related_subjects:
            related_subjects.append({
                "id": exam.subject.id,
                "name": exam.subject.name
            })
        
        # 构建响应数据
        exam_data = {
            "id": exam.id,
            "name": exam.name,
            "exam_date": exam.exam_date,
            "total_score": exam.total_score,
            "description": exam.description,
            "subjects": related_subjects,  # 改为多个科目的数组
            "participant_count": score_count
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取考试详情成功",
            data=exam_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取考试详情失败: {str(e)}"
        )

@router.put("/{exam_id}", response_model=StandardResponse, summary="更新考试信息")
async def update_exam(
    exam_id: int,
    name: Optional[str] = None,
    exam_date: Optional[datetime] = None,
    description: Optional[str] = None,
    current_user: User = Depends(check_is_teacher_or_admin)
):
    """
    更新考试信息
    
    - **exam_id**: 考试ID
    - **name**: 考试名称（可选）
    - **exam_date**: 考试日期（可选）
    - **description**: 考试描述（可选）
    
    权限要求：
    - 教师：只能更新自己任教学科的考试
    - 班主任：只能更新自己任教学科的考试
    - 管理员：可更新任何考试的信息
    - 学生：无权更新考试
    
    注意：此接口会更新同一组考试(同一个exam_id)下所有科目的共同信息
    """
    try:
        # 获取考试信息
        exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject")
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 需要更新的考试列表
        exams_to_update = [exam]
        
        # 如果有exam_id，则获取相关考试进行批量更新
        if exam.exam_id:
            related_exams = await Exam.filter(exam_id=exam.exam_id).exclude(id=exam_id)
            exams_to_update.extend(related_exams)
        
        # 更新字段
        updated_exams = []
        for exam_obj in exams_to_update:
            if name:
                exam_obj.name = name
            if exam_date:
                exam_obj.exam_date = exam_date
            if description is not None:  # 允许设置为空字符串
                exam_obj.description = description
            
            await exam_obj.save()
            # 预加载关联数据以便返回
            await exam_obj.fetch_related("subject")
            updated_exams.append(exam_obj)
        
        # 获取更新后的科目列表
        related_subjects = []
        for updated_exam in updated_exams:
            related_subjects.append({
                "id": updated_exam.subject.id,
                "name": updated_exam.subject.name
            })
        
        # 构建响应数据
        exam_data = {
            "id": exam.id,
            "name": exam.name,
            "exam_date": exam.exam_date,
            "total_score": exam.total_score,
            "description": exam.description,
            "subjects": related_subjects,
            "updated_count": len(updated_exams)
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message=f"考试信息更新成功，共更新{len(updated_exams)}个科目",
            data=exam_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新考试信息失败: {str(e)}"
        )

@router.delete("/{exam_id}", response_model=StandardResponse, summary="删除考试")
async def delete_exam(
    exam_id: int,
    delete_all: bool = Query(False, description="是否删除同一考试组下的所有科目考试"),
    current_user: User = Depends(check_is_admin)
):
    """
    删除考试
    
    - **exam_id**: 考试ID
    - **delete_all**: 是否删除同一考试组下的所有科目考试（默认False）
    
    权限要求：
    - 管理员：可删除任何无成绩记录的考试
    - 教师/班主任/学生：无权删除考试
    """
    try:
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 需要删除的考试列表
        exams_to_delete = [exam]
        
        # 如果要删除整个考试组，获取相关考试
        if delete_all and exam.exam_id:
            related_exams = await Exam.filter(exam_id=exam.exam_id).exclude(id=exam_id)
            exams_to_delete.extend(related_exams)
        
        # 检查是否有成绩关联到这些考试
        for exam_obj in exams_to_delete:
            score_count = await exam_obj.scores.all().count()
            if score_count > 0:
                return create_error_response(
                    status.HTTP_400_BAD_REQUEST, 
                    f"无法删除考试ID={exam_obj.id}，该考试下有{score_count}条成绩记录"
                )
        
        # 删除考试
        deleted_count = 0
        for exam_obj in exams_to_delete:
            await exam_obj.delete()
            deleted_count += 1
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message=f"考试删除成功，共删除{deleted_count}个科目考试",
            data={"deleted_count": deleted_count},
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除考试失败: {str(e)}"
        )

@router.get("/groups", response_model=StandardResponse, summary="获取考试组列表")
async def get_exam_groups(
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取考试组列表，每个考试组包含多个学科的考试
    
    - **search**: 搜索关键词（可选，按名称或描述搜索）
    - **start_date**: 开始日期（可选，按日期范围筛选）
    - **end_date**: 结束日期（可选，按日期范围筛选）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己参与的考试组
    - 教师：可查看自己任教学科的考试组
    - 班主任：可查看自己任教学科和管理班级所有学科的考试组
    - 管理员：可查看所有考试组
    """
    try:
        # 只查询有exam_id的考试
        query = Exam.filter(exam_id__not_isnull=True).prefetch_related("subject")
        
        # 根据日期范围筛选
        if start_date:
            query = query.filter(exam_date__gte=start_date)
        if end_date:
            query = query.filter(exam_date__lte=end_date)
            
        # 搜索
        if search:
            query = query.filter(name__icontains=search) | query.filter(description__icontains=search)
        
        # 获取所有符合条件的考试
        all_exams = await query.order_by("-exam_date")
        
        # 按exam_id将考试分组
        exam_groups = {}
        for exam in all_exams:
            if exam.exam_id not in exam_groups:
                exam_groups[exam.exam_id] = {
                    "id": exam.id,  # 使用组内第一个考试的ID
                    "group_id": exam.exam_id,
                    "name": exam.name,
                    "exam_date": exam.exam_date,
                    "description": exam.description,
                    "subjects": [],
                    "subject_count": 0
                }
            # 添加科目信息
            exam_groups[exam.exam_id]["subjects"].append({
                "id": exam.subject.id,
                "name": exam.subject.name,
                "total_score": exam.total_score
            })
            exam_groups[exam.exam_id]["subject_count"] += 1
        
        # 转换为列表并分页
        group_list = list(exam_groups.values())
        group_list.sort(key=lambda x: x["exam_date"], reverse=True)
        
        # 计算总数
        total = len(group_list)
        
        # 应用分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_groups = group_list[start_idx:end_idx]
        
        # 创建响应数据
        response_data = {
            "items": paginated_groups,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取考试组列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取考试组列表失败: {str(e)}"
        ) 