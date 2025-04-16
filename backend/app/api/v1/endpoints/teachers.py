from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import check_is_admin, check_is_teacher_or_admin
from app.models.enums import UserRole
from app.models.user import User
from app.models.teacher import Teacher
from app.models.subject import Subject
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

@router.post("/", response_model=StandardResponse, summary="创建教师信息")
async def create_teacher(
    name: str,
    teacher_code: str,
    subject_id: int,
    user_id: int,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    创建教师信息
    
    - **name**: 教师姓名
    - **teacher_code**: 教师编号
    - **subject_id**: 学科ID
    - **user_id**: 用户ID
    - **phone**: 联系电话（可选）
    - **email**: 电子邮箱（可选）
    
    权限要求：
    - 管理员：可创建任何教师信息
    - 班主任/教师/学生：无权创建教师信息
    """
    try:
        # 检查用户是否存在
        user = await User.get_or_none(id=user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{user_id}的用户"
            )
        
        # 检查学科是否存在
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的学科"
            )
        
        # 检查教师编号是否已存在
        existing_teacher = await Teacher.get_or_none(teacher_code=teacher_code)
        if existing_teacher:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"教师编号为{teacher_code}的教师已存在"
            )
        
        # 检查用户是否已关联教师
        existing_teacher_user = await Teacher.get_or_none(user_id=user_id)
        if existing_teacher_user:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"该用户已关联其他教师"
            )
        
        # 创建教师
        teacher = await Teacher.create(
            name=name,
            teacher_code=teacher_code,
            subject_id=subject_id,
            user_id=user_id,
            phone=phone,
            email=email
        )
        
        # 预加载关联数据以便返回
        await teacher.fetch_related("subject")
        
        # 转换为响应数据
        teacher_data = {
            "id": teacher.id,
            "name": teacher.name,
            "teacher_code": teacher.teacher_code,
            "phone": teacher.phone,
            "email": teacher.email,
            "subject": {
                "id": teacher.subject.id,
                "name": teacher.subject.name
            },
            "user_id": teacher.user_id
        }
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="教师创建成功",
            data=teacher_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建教师失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取教师列表")
async def get_teachers(
    subject_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取教师列表，支持分页和筛选
    
    - **subject_id**: 学科ID（可选，按学科筛选）
    - **search**: 搜索关键词（可选，按姓名、教师编号或邮箱搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：可查看自己班级的任课教师
    - 教师/班主任：可查看同校所有教师
    - 管理员：可查看所有教师
    """
    try:
        # 构建查询
        query = Teacher.all().prefetch_related("subject")
        
        # 根据学科筛选
        if subject_id:
            query = query.filter(subject_id=subject_id)
            
        # 根据关键词搜索
        if search:
            query = query.filter(
                name__icontains=search
            ) | query.filter(
                teacher_code__icontains=search
            ) | query.filter(
                email__icontains=search
            )
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        teachers = await query.order_by("name").offset((page - 1) * page_size).limit(page_size)
        
        # 转换为响应数据
        teacher_list = []
        for teacher in teachers:
            # 获取该教师是否为班主任的班级
            headteacher_classes = await Class.filter(headteacher_id=teacher.id).values("id", "name")
            
            # 获取该教师任教的班级
            teaching_classes = await teacher.teaching_classes.all().values("id", "name")
            
            teacher_data = {
                "id": teacher.id,
                "name": teacher.name,
                "teacher_code": teacher.teacher_code,
                "phone": teacher.phone,
                "email": teacher.email,
                "subject": {
                    "id": teacher.subject.id,
                    "name": teacher.subject.name
                },
                "headteacher_classes": headteacher_classes,
                "teaching_classes": teaching_classes
            }
            teacher_list.append(teacher_data)
        
        # 创建分页响应
        paginated_response = {
            "items": teacher_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取教师列表成功",
            data=paginated_response,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取教师列表失败: {str(e)}"
        )

@router.get("/{teacher_id}", response_model=StandardResponse, summary="获取教师详情")
async def get_teacher(
    teacher_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取教师详细信息
    
    - **teacher_id**: 教师ID
    
    权限要求：
    - 学生：只能查看自己班级的任课教师信息
    - 教师：可查看自己的信息和同校其他教师的基本信息
    - 班主任：可查看自己的信息和同校其他教师的基本信息
    - 管理员：可查看任何教师的详细信息
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id).prefetch_related("subject", "user")
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 获取该教师是否为班主任的班级
        headteacher_classes = await Class.filter(headteacher_id=teacher.id).prefetch_related("grade")
        
        headteacher_classes_data = []
        for cls in headteacher_classes:
            grade_name = cls.grade.name if hasattr(cls, "grade") else ""
            headteacher_classes_data.append({
                "id": cls.id,
                "name": cls.name,
                "grade_name": grade_name,
                "full_name": f"{grade_name}{cls.name}" if grade_name else cls.name
            })
        
        # 获取该教师任教的班级
        teaching_classes = await teacher.teaching_classes.all().prefetch_related("grade")
        
        teaching_classes_data = []
        for cls in teaching_classes:
            grade_name = cls.grade.name if hasattr(cls, "grade") else ""
            teaching_classes_data.append({
                "id": cls.id,
                "name": cls.name,
                "grade_name": grade_name,
                "full_name": f"{grade_name}{cls.name}" if grade_name else cls.name
            })
        
        # 转换为响应数据
        teacher_data = {
            "id": teacher.id,
            "name": teacher.name,
            "teacher_code": teacher.teacher_code,
            "phone": teacher.phone,
            "email": teacher.email,
            "subject": {
                "id": teacher.subject.id,
                "name": teacher.subject.name
            },
            "user_id": teacher.user_id,
            "username": teacher.user.username,
            "headteacher_classes": headteacher_classes_data,
            "teaching_classes": teaching_classes_data
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取教师详情成功",
            data=teacher_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取教师详情失败: {str(e)}"
        )

@router.put("/{teacher_id}", response_model=StandardResponse, summary="更新教师信息")
async def update_teacher(
    teacher_id: int,
    name: Optional[str] = None,
    teacher_code: Optional[str] = None,
    subject_id: Optional[int] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    更新教师信息
    
    - **teacher_id**: 教师ID
    - **name**: 教师姓名（可选）
    - **teacher_code**: 教师编号（可选）
    - **subject_id**: 学科ID（可选）
    - **phone**: 联系电话（可选）
    - **email**: 电子邮箱（可选）
    
    权限要求：
    - 管理员：可更新任何教师信息
    - 班主任/教师/学生：无权更新教师信息
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 检查教师编号是否已存在（如果修改了编号）
        if teacher_code and teacher_code != teacher.teacher_code:
            existing_teacher = await Teacher.get_or_none(teacher_code=teacher_code)
            if existing_teacher and existing_teacher.id != teacher_id:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    f"教师编号为{teacher_code}的教师已存在"
                )
            teacher.teacher_code = teacher_code
        
        # 检查学科是否存在（如果修改了学科）
        if subject_id and subject_id != teacher.subject_id:
            subject = await Subject.get_or_none(id=subject_id)
            if not subject:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{subject_id}的学科"
                )
            teacher.subject_id = subject_id
        
        # 更新教师信息
        if name:
            teacher.name = name
        if phone is not None:  # 允许设置为空字符串
            teacher.phone = phone
        if email is not None:  # 允许设置为空字符串
            teacher.email = email
        
        await teacher.save()
        
        # 预加载关联数据以便返回
        await teacher.fetch_related("subject")
        
        # 转换为响应数据
        teacher_data = {
            "id": teacher.id,
            "name": teacher.name,
            "teacher_code": teacher.teacher_code,
            "phone": teacher.phone,
            "email": teacher.email,
            "subject": {
                "id": teacher.subject.id,
                "name": teacher.subject.name
            },
            "user_id": teacher.user_id
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师信息更新成功",
            data=teacher_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新教师信息失败: {str(e)}"
        )

@router.delete("/{teacher_id}", response_model=StandardResponse, summary="删除教师")
async def delete_teacher(
    teacher_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    删除教师信息
    
    - **teacher_id**: 教师ID
    
    权限要求：
    - 管理员：可删除任何教师
    - 班主任/教师/学生：无权删除教师
    """
    try:
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 检查是否有班级以该教师为班主任
        headteacher_classes = await Class.filter(headteacher_id=teacher_id).count()
        if headteacher_classes > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除教师，该教师是{headteacher_classes}个班级的班主任"
            )
        
        # 获取该教师的用户ID，以便后续可能的用户删除
        user_id = teacher.user_id
        
        # 删除该教师与任教班级的关联关系
        await teacher.teaching_classes.clear()
        
        # 删除教师
        await teacher.delete()
        
        # 可选：同时删除关联的用户账号
        # await User.filter(id=user_id).delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除教师失败: {str(e)}"
        )

@router.post("/{teacher_id}/classes/{class_id}", response_model=StandardResponse, summary="将教师分配到班级")
async def assign_teacher_to_class(
    teacher_id: int,
    class_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    将教师分配到班级（添加为任课教师）
    
    - **teacher_id**: 教师ID
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可将任何教师分配到任何班级
    - 班主任/教师/学生：无权分配教师到班级
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 获取班级信息
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查教师是否已经是该班级的任课教师
        existing_relationship = await teacher.teaching_classes.filter(id=class_id).exists()
        if existing_relationship:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                "该教师已经是该班级的任课教师"
            )
        
        # 添加教师为班级的任课教师
        await teacher.teaching_classes.add(class_obj)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师成功分配到班级",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"分配教师到班级失败: {str(e)}"
        )

@router.delete("/{teacher_id}/classes/{class_id}", response_model=StandardResponse, summary="从班级移除教师")
async def remove_teacher_from_class(
    teacher_id: int,
    class_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    从班级中移除教师（取消任课教师身份）
    
    - **teacher_id**: 教师ID
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可从任何班级移除任何教师
    - 班主任/教师/学生：无权从班级移除教师
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 获取班级信息
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查教师是否是该班级的任课教师
        existing_relationship = await teacher.teaching_classes.filter(id=class_id).exists()
        if not existing_relationship:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                "该教师不是该班级的任课教师"
            )
        
        # 如果教师是班主任，不允许移除教师与班级的关联
        if class_obj.headteacher_id == teacher_id:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                "无法移除，该教师是该班级的班主任"
            )
        
        # 移除教师与班级的关联
        await teacher.teaching_classes.remove(class_obj)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师已从班级移除",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"从班级移除教师失败: {str(e)}"
        )

@router.post("/{teacher_id}/headteacher/{class_id}", response_model=StandardResponse, summary="设置教师为班主任")
async def set_headteacher(
    teacher_id: int,
    class_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    设置教师为班主任
    
    - **teacher_id**: 教师ID
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可设置任何教师为任何班级的班主任
    - 班主任/教师/学生：无权设置班主任
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 获取班级信息
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查班级是否已有班主任
        if class_obj.headteacher_id and class_obj.headteacher_id != teacher_id:
            old_headteacher = await Teacher.get(id=class_obj.headteacher_id)
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"该班级已有班主任：{old_headteacher.name}"
            )
        
        # 设置为班主任
        class_obj.headteacher_id = teacher_id
        await class_obj.save()
        
        # 同时确保教师是班级的任课教师
        existing_relationship = await teacher.teaching_classes.filter(id=class_id).exists()
        if not existing_relationship:
            await teacher.teaching_classes.add(class_obj)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师成功设置为班主任",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"设置班主任失败: {str(e)}"
        )

@router.delete("/{teacher_id}/headteacher/{class_id}", response_model=StandardResponse, summary="取消班主任职务")
async def remove_headteacher(
    teacher_id: int,
    class_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    取消教师的班主任身份
    
    - **teacher_id**: 教师ID
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可取消任何班级的班主任职务
    - 班主任/教师/学生：无权取消班主任职务
    """
    try:
        # 获取教师信息
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 获取班级信息
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查教师是否是该班级的班主任
        if class_obj.headteacher_id != teacher_id:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                "该教师不是该班级的班主任"
            )
        
        # 取消班主任身份
        class_obj.headteacher_id = None
        await class_obj.save()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="已取消班主任身份",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"取消班主任身份失败: {str(e)}"
        ) 