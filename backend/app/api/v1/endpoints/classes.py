from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import pandas as pd

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import check_is_admin, check_is_headteacher_or_admin, check_class_access
from app.models.enums import UserRole
from app.models.user import User
from app.models.grade import Grade
from app.models.class_model import Class
from app.models.teacher import Teacher
from app.models.student import Student
from app.schemas.common import StandardResponse, PaginatedResponse
from app.utils.excel_utils import ExcelUtils

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

@router.post("/", response_model=StandardResponse, summary="创建班级")
async def create_class(
    name: str,
    code: str,
    grade_id: int,
    capacity: int = 0,
    headteacher_id: Optional[int] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    创建班级
    
    - **name**: 班级名称
    - **code**: 班级代码
    - **grade_id**: 年级ID
    - **capacity**: 班级容量（可选，默认0表示不限）
    - **headteacher_id**: 班主任ID（可选）
    
    权限要求：
    - 管理员：可创建任何班级
    - 班主任/教师/学生：无权创建班级
    """
    try:
        # 检查班级代码是否已存在
        existing_class = await Class.get_or_none(code=code)
        if existing_class:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"班级代码'{code}'已存在"
            )
        
        # 检查年级是否存在
        grade = await Grade.get_or_none(id=grade_id)
        if not grade:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{grade_id}的年级"
            )
        
        # 创建班级数据
        class_data = {
            "name": name,
            "code": code,
            "grade_id": grade_id,
            "capacity": capacity
        }
        
        # 检查班主任是否存在
        if headteacher_id:
            teacher = await Teacher.get_or_none(id=headteacher_id)
            if not teacher:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{headteacher_id}的教师"
                )
            class_data["headteacher_id"] = headteacher_id
        
        # 创建班级
        class_obj = await Class.create(**class_data)
        
        # 预加载关联数据以便返回
        await class_obj.fetch_related("grade")
        if headteacher_id:
            await class_obj.fetch_related("headteacher")
        
        # 构建响应数据
        response_data = {
            "id": class_obj.id,
            "name": class_obj.name,
            "code": class_obj.code,
            "capacity": class_obj.capacity,
            "grade": {
                "id": class_obj.grade.id,
                "name": class_obj.grade.name,
                "code": class_obj.grade.code
            }
        }
        
        if hasattr(class_obj, "headteacher") and class_obj.headteacher:
            response_data["headteacher"] = {
                "id": class_obj.headteacher.id,
                "name": class_obj.headteacher.name
            }
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="班级创建成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建班级失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取班级列表")
async def get_classes(
    grade_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级列表，支持分页和筛选
    
    - **grade_id**: 年级ID（可选，按年级筛选）
    - **search**: 搜索关键词（可选，按班级名称或代码搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：只能查看自己所在的班级
    - 教师：可查看自己任教的班级
    - 班主任：可查看自己管理的班级和同年级的其他班级
    - 管理员：可查看所有班级
    """
    try:
        # 构建查询
        query = Class.all().prefetch_related("grade", "headteacher")
        
        # 根据权限筛选
        if current_user.role == UserRole.TEACHER or current_user.role == UserRole.HEADTEACHER:
            # 教师只能看到自己任教的班级
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if teacher:
                if current_user.role == UserRole.HEADTEACHER:
                    # 班主任可以看到自己管理的和任教的班级
                    classes_taught = await Class.filter(teachers__id=teacher.id)
                    class_managed = await Class.filter(headteacher_id=teacher.id)
                    class_ids = set([cls.id for cls in classes_taught] + [cls.id for cls in class_managed])
                    if not class_ids:
                        return create_error_response(
                            status.HTTP_404_NOT_FOUND,
                            "您没有管理或任教的班级"
                        )
                    query = query.filter(id__in=class_ids)
                else:
                    # 普通教师只能看到自己任教的班级
                    classes_taught = await Class.filter(teachers__id=teacher.id)
                    if not classes_taught:
                        return create_error_response(
                            status.HTTP_404_NOT_FOUND,
                            "您没有任教的班级"
                        )
                    query = query.filter(id__in=[cls.id for cls in classes_taught])
        elif current_user.role == UserRole.STUDENT:
            # 学生只能看到自己所在的班级
            student = await Student.get_or_none(user_id=current_user.id)
            if student and student.class_field_id:
                query = query.filter(id=student.class_field_id)
            else:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND,
                    "您没有所属的班级"
                )
        
        # 筛选条件
        if grade_id:
            query = query.filter(grade_id=grade_id)
            
        if search:
            query = query.filter(name__icontains=search) | query.filter(code__icontains=search)
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        classes = await query.offset((page - 1) * page_size).limit(page_size)
        
        # 转换为响应数据
        class_list = []
        for class_obj in classes:
            class_data = {
                "id": class_obj.id,
                "name": class_obj.name,
                "code": class_obj.code,
                "capacity": class_obj.capacity,
                "grade": {
                    "id": class_obj.grade.id,
                    "name": class_obj.grade.name,
                    "code": class_obj.grade.code
                }
            }
            
            if hasattr(class_obj, "headteacher") and class_obj.headteacher:
                class_data["headteacher"] = {
                    "id": class_obj.headteacher.id,
                    "name": class_obj.headteacher.name
                }
            
            class_list.append(class_data)
        
        # 创建响应数据
        response_data = {
            "items": class_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级列表成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取班级列表失败: {str(e)}"
        )

@router.get("/{class_id}", response_model=StandardResponse, summary="获取班级详情")
async def get_class(
    class_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级详细信息
    
    - **class_id**: 班级ID
    
    权限要求：
    - 学生：只能查看自己所在的班级
    - 教师：可查看自己任教的班级
    - 班主任：可查看自己管理的班级和同年级的其他班级
    - 管理员：可查看任何班级
    """
    try:
        # 检查用户是否有权限访问该班级
        await check_class_access(class_id, current_user)
        
        # 获取班级详情
        class_obj = await Class.get_or_none(id=class_id).prefetch_related(
            "grade", "headteacher", "students", "teachers"
        )
        
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 统计班级学生数量
        student_count = await class_obj.students.all().count()
        
        # 构建响应数据
        class_data = {
            "id": class_obj.id,
            "name": class_obj.name,
            "code": class_obj.code,
            "capacity": class_obj.capacity,
            "student_count": student_count,
            "grade": {
                "id": class_obj.grade.id,
                "name": class_obj.grade.name,
                "code": class_obj.grade.code
            }
        }
        
        if hasattr(class_obj, "headteacher") and class_obj.headteacher:
            class_data["headteacher"] = {
                "id": class_obj.headteacher.id,
                "name": class_obj.headteacher.name,
                "teacher_code": class_obj.headteacher.teacher_code
            }
        
        # 获取班级教师列表
        teachers = await class_obj.teachers.all().prefetch_related("subject")
        if teachers:
            teachers_data = []
            for teacher in teachers:
                teacher_data = {
                    "id": teacher.id,
                    "name": teacher.name,
                    "teacher_code": teacher.teacher_code
                }
                
                if hasattr(teacher, "subject") and teacher.subject:
                    teacher_data["subject"] = {
                        "id": teacher.subject.id,
                        "name": teacher.subject.name
                    }
                
                teachers_data.append(teacher_data)
            
            class_data["teachers"] = teachers_data
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级详情成功",
            data=class_data,
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
            f"获取班级详情失败: {str(e)}"
        )

@router.put("/{class_id}", response_model=StandardResponse, summary="更新班级信息")
async def update_class(
    class_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    grade_id: Optional[int] = None,
    capacity: Optional[int] = None,
    headteacher_id: Optional[int] = None,
    current_user: User = Depends(check_is_admin)
):
    """
    更新班级信息
    
    - **class_id**: 班级ID
    - **name**: 班级名称（可选）
    - **code**: 班级代码（可选）
    - **grade_id**: 年级ID（可选）
    - **capacity**: 班级容量（可选）
    - **headteacher_id**: 班主任ID（可选）
    
    权限要求：
    - 管理员：可更新任何班级的信息
    - 班主任/教师/学生：无权更新班级信息
    """
    try:
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查班级代码是否重复
        if code and code != class_obj.code:
            existing_class = await Class.get_or_none(code=code)
            if existing_class:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    f"班级代码'{code}'已存在"
                )
        
        # 检查年级是否存在
        if grade_id:
            grade = await Grade.get_or_none(id=grade_id)
            if not grade:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{grade_id}的年级"
                )
            class_obj.grade_id = grade_id
        
        # 更新字段
        if name:
            class_obj.name = name
        if code:
            class_obj.code = code
        if capacity is not None:
            class_obj.capacity = capacity
        
        # 处理班主任
        if headteacher_id is not None:
            if headteacher_id == 0:  # 特殊约定：0表示移除班主任
                class_obj.headteacher_id = None
            else:
                teacher = await Teacher.get_or_none(id=headteacher_id)
                if not teacher:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND, 
                        f"未找到ID为{headteacher_id}的教师"
                    )
                class_obj.headteacher_id = headteacher_id
        
        await class_obj.save()
        
        # 预加载关联数据以便返回
        await class_obj.fetch_related("grade")
        if class_obj.headteacher_id:
            await class_obj.fetch_related("headteacher")
        
        # 构建响应数据
        response_data = {
            "id": class_obj.id,
            "name": class_obj.name,
            "code": class_obj.code,
            "capacity": class_obj.capacity,
            "grade": {
                "id": class_obj.grade.id,
                "name": class_obj.grade.name,
                "code": class_obj.grade.code
            }
        }
        
        if hasattr(class_obj, "headteacher") and class_obj.headteacher:
            response_data["headteacher"] = {
                "id": class_obj.headteacher.id,
                "name": class_obj.headteacher.name
            }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="班级信息更新成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新班级信息失败: {str(e)}"
        )

@router.delete("/{class_id}", response_model=StandardResponse, summary="删除班级")
async def delete_class(
    class_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    删除班级
    
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可删除任何班级
    - 班主任/教师/学生：无权删除班级
    """
    try:
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查是否有学生关联到这个班级
        student_count = await class_obj.students.all().count()
        if student_count > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除班级，该班级下有{student_count}名学生"
            )
        
        # 删除班级
        await class_obj.delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="班级删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除班级失败: {str(e)}"
        )

@router.post("/{class_id}/teachers/{teacher_id}", response_model=StandardResponse, summary="添加教师到班级")
async def add_teacher_to_class(
    class_id: int,
    teacher_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    添加教师到班级（设置为任课教师）
    
    - **class_id**: 班级ID
    - **teacher_id**: 教师ID
    
    权限要求：
    - 管理员：可添加任何教师到任何班级
    - 班主任/教师/学生：无权添加教师到班级
    """
    try:
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 检查教师是否已经在班级中
        exists = await class_obj.teachers.filter(id=teacher_id).exists()
        if exists:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"教师已经是该班级的任课教师"
            )
        
        # 添加关联
        await class_obj.teachers.add(teacher)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="教师添加到班级成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"添加教师到班级失败: {str(e)}"
        )

@router.delete("/{class_id}/teachers/{teacher_id}", response_model=StandardResponse, summary="从班级移除教师")
async def remove_teacher_from_class(
    class_id: int,
    teacher_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    从班级移除教师（取消任课教师身份）
    
    - **class_id**: 班级ID
    - **teacher_id**: 教师ID
    
    权限要求：
    - 管理员：可从任何班级移除任何教师
    - 班主任/教师/学生：无权从班级移除教师
    """
    try:
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        teacher = await Teacher.get_or_none(id=teacher_id)
        if not teacher:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{teacher_id}的教师"
            )
        
        # 检查教师是否在班级中
        exists = await class_obj.teachers.filter(id=teacher_id).exists()
        if not exists:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"教师不是该班级的任课教师"
            )
        
        # 移除关联
        await class_obj.teachers.remove(teacher)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="从班级移除教师成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"从班级移除教师失败: {str(e)}"
        )

@router.get("/export", response_class=StreamingResponse, summary="导出班级信息Excel")
async def export_classes(
    grade_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    导出班级信息到Excel文件
    
    - **grade_id**: 年级ID（可选，按年级筛选）
    
    权限要求：
    - 管理员：可导出任何班级的信息
    - 班主任：可导出自己管理的班级和同年级其他班级的信息
    - 教师：可导出自己任教班级的信息
    - 学生：无权导出班级信息
    """
    try:
        # 构建查询
        query = Class.all().prefetch_related("grade", "headteacher")
        
        # 年级筛选
        if grade_id:
            query = query.filter(grade_id=grade_id)
        
        # 获取班级列表
        classes = await query.order_by("grade__name", "name")
        
        # 准备导出数据
        data = []
        for cls in classes:
            # 获取班级人数
            student_count = await Student.filter(class_field_id=cls.id).count()
            
            # 准备班主任信息
            headteacher_name = cls.headteacher.name if cls.headteacher else ""
            headteacher_code = cls.headteacher.teacher_code if cls.headteacher else ""
            
            # 获取任课教师列表
            teachers = await cls.teachers.all().prefetch_related("subject")
            teacher_info = []
            for teacher in teachers:
                subject_name = teacher.subject.name if hasattr(teacher.subject, "name") else ""
                teacher_info.append(f"{teacher.name}({subject_name})")
            
            teacher_str = "、".join(teacher_info)
            
            # 创建数据行
            class_data = {
                "id": cls.id,
                "grade_name": cls.grade.name if hasattr(cls.grade, "name") else "",
                "class_name": cls.name,
                "full_name": f"{cls.grade.name}{cls.name}" if hasattr(cls.grade, "name") else cls.name,
                "capacity": cls.capacity,
                "student_count": student_count,
                "headteacher_name": headteacher_name,
                "headteacher_code": headteacher_code,
                "teachers": teacher_str,
                "description": cls.description or ""
            }
            data.append(class_data)
        
        # 定义列映射
        columns = [
            ("grade_name", "年级"),
            ("class_name", "班级"),
            ("full_name", "班级全称"),
            ("capacity", "容量"),
            ("student_count", "学生数量"),
            ("headteacher_name", "班主任"),
            ("headteacher_code", "班主任编号"),
            ("teachers", "任课教师"),
            ("description", "描述")
        ]
        
        # 生成Excel文件
        title = "班级信息表"
        if grade_id:
            grade = await Grade.get_or_none(id=grade_id)
            if grade:
                title = f"{grade.name}班级信息表"
        
        output = ExcelUtils.write_excel(data, columns, title)
        
        # 生成文件名
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"班级信息表_{now}.xlsx"
        
        # 返回Excel文件
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出班级信息失败: {str(e)}"
        )

@router.post("/import", response_model=StandardResponse, summary="从Excel导入班级信息")
async def import_classes(
    file: UploadFile = File(...),
    grade_id: int = Form(...),
    current_user: User = Depends(check_is_admin)
):
    """
    从Excel导入班级信息
    
    - **file**: Excel文件
    - **grade_id**: 年级ID
    
    权限要求：
    - 管理员：可导入班级信息到任何年级
    - 班主任/教师/学生：无权导入班级信息
    """
    try:
        # 检查年级是否存在
        grade = await Grade.get_or_none(id=grade_id)
        if not grade:
            return StandardResponse(
                code=status.HTTP_404_NOT_FOUND,
                message=f"未找到ID为{grade_id}的年级",
                data=None,
                timestamp=datetime.now()
            )
        
        # 读取Excel文件
        df = await ExcelUtils.read_excel(file)
        
        # 检查必填列
        required_columns = ["班级名称"]
        for column in required_columns:
            if column not in df.columns:
                return StandardResponse(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Excel文件缺少必填列: {column}",
                    data=None,
                    timestamp=datetime.now()
                )
        
        # 验证数据
        def validate_class_name(name):
            if not isinstance(name, str) or len(name) < 1 or len(name) > 20:
                return "班级名称长度应在1-20个字符之间"
            return True
            
        validators = {
            "班级名称": validate_class_name
        }
        
        is_valid, errors = ExcelUtils.validate_data(df, required_columns, validators)
        
        if not is_valid:
            return StandardResponse(
                code=status.HTTP_400_BAD_REQUEST,
                message="导入数据验证失败",
                data={"errors": errors},
                timestamp=datetime.now()
            )
        
        # 转换列名
        df = df.rename(columns={
            "班级名称": "name",
            "容量": "capacity",
            "班主任编号": "headteacher_code",
            "描述": "description"
        })
        
        # 填充缺失的可选列
        optional_columns = ["capacity", "headteacher_code", "description"]
        for col in optional_columns:
            if col not in df.columns:
                df[col] = None
        
        # 查询所有教师，用于关联班主任
        teachers = await Teacher.all()
        teacher_dict = {teacher.teacher_code: teacher for teacher in teachers}
        
        # 开始导入数据
        success_count = 0
        error_count = 0
        error_details = []
        
        for idx, row in df.iterrows():
            try:
                class_name = row["name"]
                
                # 检查同年级班级名称是否已存在
                existing_class = await Class.get_or_none(grade_id=grade_id, name=class_name)
                if existing_class:
                    error_count += 1
                    error_details.append({
                        "row": idx + 2,
                        "name": class_name,
                        "error": f"'{grade.name}{class_name}'班级已存在"
                    })
                    continue
                
                # 处理班主任关联
                headteacher_id = None
                if "headteacher_code" in row and pd.notna(row["headteacher_code"]):
                    headteacher_code = str(row["headteacher_code"])
                    if headteacher_code in teacher_dict:
                        headteacher_id = teacher_dict[headteacher_code].id
                    else:
                        error_count += 1
                        error_details.append({
                            "row": idx + 2,
                            "name": class_name,
                            "error": f"未找到编号为'{headteacher_code}'的教师"
                        })
                        continue
                
                # 处理容量
                capacity = 0
                if "capacity" in row and pd.notna(row["capacity"]):
                    try:
                        capacity = int(row["capacity"])
                        if capacity < 0:
                            capacity = 0
                    except:
                        capacity = 0
                
                # 处理描述
                description = None
                if "description" in row and pd.notna(row["description"]):
                    description = str(row["description"])
                
                # 创建班级
                await Class.create(
                    name=class_name,
                    grade_id=grade_id,
                    capacity=capacity,
                    headteacher_id=headteacher_id,
                    description=description
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                error_details.append({
                    "row": idx + 2,
                    "name": row["name"] if "name" in row and pd.notna(row["name"]) else "",
                    "error": str(e)
                })
        
        # 返回结果
        return StandardResponse(
            code=status.HTTP_200_OK,
            message=f"导入完成，成功{success_count}条，失败{error_count}条",
            data={
                "success_count": success_count,
                "error_count": error_count,
                "error_details": error_details
            },
            timestamp=datetime.now()
        )
    except Exception as e:
        return StandardResponse(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"导入班级信息失败: {str(e)}",
            data=None,
            timestamp=datetime.now()
        )

@router.get("/import/template", response_class=StreamingResponse, summary="获取班级导入模板")
async def get_class_import_template(
    current_user: User = Depends(check_is_admin)
):
    """
    获取班级导入模板Excel文件
    
    权限要求：
    - 管理员：可获取班级导入模板
    - 班主任/教师/学生：无权获取班级导入模板
    """
    try:
        # 获取所有教师
        teachers = await Teacher.all().prefetch_related("subject")
        teacher_info = []
        for teacher in teachers:
            subject_name = teacher.subject.name if hasattr(teacher.subject, "name") else ""
            teacher_info.append(f"{teacher.name}({subject_name}): {teacher.teacher_code}")
        
        teacher_notes = "\n".join(teacher_info)
        
        # 准备模板数据
        data = [
            {
                "班级名称": "",
                "容量": "",
                "班主任编号": "",
                "描述": ""
            },
            {
                "班级名称": "示例：1班",
                "容量": "示例：50",
                "班主任编号": "示例：T001",
                "描述": "示例：重点班"
            }
        ]
        
        # 定义列
        columns = [
            ("班级名称", "班级名称(*)"),
            ("容量", "容量"),
            ("班主任编号", "班主任编号"),
            ("描述", "描述")
        ]
        
        # 生成Excel文件
        title = "班级导入模板"
        
        output = ExcelUtils.write_excel(data, columns, title)
        
        # 生成文件名
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"班级导入模板_{now}.xlsx"
        
        # 返回Excel文件
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取班级导入模板失败: {str(e)}"
        ) 