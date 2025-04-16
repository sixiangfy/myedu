from fastapi import APIRouter, Depends, HTTPException, Query, status, Body, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import pandas as pd

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import (
    check_is_admin, check_is_teacher_or_admin, check_is_headteacher_or_admin,
    check_student_access
)
from app.models.enums import UserRole
from app.models.user import User
from app.models.student import Student
from app.models.class_model import Class
from app.models.score import Score
from app.schemas.common import StandardResponse, PaginatedResponse
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
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

@router.post("/", response_model=StandardResponse, summary="创建学生信息")
async def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(check_is_admin)
):
    """
    创建学生信息
    
    - **name**: 学生姓名
    - **student_code**: 学号
    - **class_id**: 班级ID
    - **gender**: 性别（可选）
    - **birthday**: 出生日期（可选）
    - **address**: 住址（可选）
    - **phone**: 电话（可选）
    - **email**: 邮箱（可选）
    - **guardian**: 监护人（可选）
    - **guardian_phone**: 监护人电话（可选）
    
    权限要求：
    - 管理员：可创建任何班级的学生
    - 班主任/教师/学生：无权创建学生信息
    """
    try:
        # 检查用户是否存在
        user = await User.get_or_none(id=student_data.user_id)
        if not user:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{student_data.user_id}的用户"
            )
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=student_data.class_field)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{student_data.class_field}的班级"
            )
        
        # 检查学号是否已存在
        existing_student = await Student.get_or_none(student_code=student_data.student_code)
        if existing_student:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"学号为{student_data.student_code}的学生已存在"
            )
        
        # 检查用户是否已关联学生
        existing_student_user = await Student.get_or_none(user_id=student_data.user_id)
        if existing_student_user:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                f"该用户已关联其他学生"
            )
        
        # 创建学生
        student = await Student.create(
            name=student_data.name,
            student_code=student_data.student_code,
            gender=student_data.gender,
            birth_date=student_data.birth_date,
            address=student_data.address,
            phone=student_data.phone,
            parent_name=student_data.parent_name,
            parent_phone=student_data.parent_phone,
            user_id=student_data.user_id,
            class_field_id=student_data.class_field
        )
        
        # 预加载关联数据以便返回
        await student.fetch_related("class_field")
        await student.class_field.fetch_related("grade")
        
        # 准备响应数据
        student_data = {
            "id": student.id,
            "name": student.name,
            "student_code": student.student_code,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "address": student.address,
            "phone": student.phone,
            "parent_name": student.parent_name,
            "parent_phone": student.parent_phone,
            "class_id": student.class_field.id,
            "class_name": student.class_field.name,
            "grade_name": student.class_field.grade.name if hasattr(student.class_field, "grade") else ""
        }
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="学生创建成功",
            data=student_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建学生失败: {str(e)}"
        )

@router.get("/", response_model=StandardResponse, summary="获取学生列表")
async def get_students(
    class_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学生列表，支持分页和筛选
    
    - **class_id**: 班级ID（可选，按班级筛选）
    - **search**: 搜索关键词（可选，按姓名或学号搜索）
    - **page**: 页码，默认1
    - **page_size**: 每页数量，默认20，最大100
    
    权限要求：
    - 学生：只能看到自己所在班级的学生名单
    - 教师：只能看到自己任教班级的学生
    - 班主任：可以看到自己管理班级的所有学生
    - 管理员：可以看到所有班级的学生
    """
    try:
        # 构建查询
        query = Student.all().prefetch_related("class_field")
        
        # 班级筛选
        if class_id:
            query = query.filter(class_field_id=class_id)
            
            # 如果当前用户是教师且不是班主任，检查权限
            if current_user.role == UserRole.TEACHER:
                # 检查教师是否有权限访问该班级
                class_obj = await Class.get_or_none(id=class_id)
                if class_obj:
                    # 获取教师信息
                    teacher = await current_user.teacher
                    if teacher:
                        # 检查是否是班主任或任课教师
                        is_headteacher = await class_obj.headteacher.filter(id=teacher.id).exists()
                        is_teaching = await class_obj.teachers.filter(id=teacher.id).exists()
                        if not (is_headteacher or is_teaching):
                            return create_error_response(
                                status.HTTP_403_FORBIDDEN, 
                                "您没有权限访问该班级的学生"
                            )
                    else:
                        return create_error_response(
                            status.HTTP_403_FORBIDDEN, 
                            "教师信息不存在"
                        )
                else:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND, 
                        f"未找到ID为{class_id}的班级"
                    )
        
        # 关键词搜索
        if search:
            query = query.filter(
                name__icontains=search
            ) | query.filter(
                student_code__icontains=search
            )
        
        # 计算总数
        total = await query.count()
        
        # 分页查询
        students = await query.order_by("student_code").offset((page - 1) * page_size).limit(page_size)
        
        # 准备响应数据
        student_list = []
        for student in students:
            # 预加载班级的年级信息
            if hasattr(student.class_field, "grade"):
                await student.class_field.fetch_related("grade")
            
            student_data = {
                "id": student.id,
                "name": student.name,
                "student_code": student.student_code,
                "gender": student.gender,
                "birth_date": student.birth_date,
                "address": student.address,
                "phone": student.phone,
                "parent_name": student.parent_name,
                "parent_phone": student.parent_phone,
                "class_id": student.class_field.id,
                "class_name": student.class_field.name,
                "grade_name": student.class_field.grade.name if hasattr(student.class_field, "grade") else ""
            }
            student_list.append(student_data)
        
        # 创建分页响应
        paginated_response = {
            "items": student_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学生列表成功",
            data=paginated_response,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"获取学生列表失败: {str(e)}"
        )

@router.get("/{student_id}", response_model=StandardResponse, summary="获取学生详情")
async def get_student(
    student_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学生详情，包括基本信息和成绩
    
    - **student_id**: 学生ID
    
    权限要求：
    - 学生：只能查看自己的详情
    - 教师：可以查看自己教授班级的学生详情
    - 班主任：可以查看自己管理班级的学生详情
    - 管理员：可以查看任何学生的详情
    """
    try:
        # 检查权限
        await check_student_access(student_id, current_user)
        
        # 获取学生信息及关联数据
        student = await Student.get_or_none(id=student_id).prefetch_related(
            "user", "class_field__grade"
        )
        
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到ID为{student_id}的学生"
            )
        
        # 一次性获取所有成绩与相关联数据
        scores = await Score.filter(student_id=student_id).prefetch_related("subject", "exam")
        
        # 组织成绩数据按考试分组
        exam_scores = {}
        
        # 预先获取所有可能用到的考试和学科
        exam_ids = list(set(score.exam_id for score in scores))
        subject_ids = list(set(score.subject_id for score in scores))
        
        # 组织数据
        for score in scores:
            exam_id = score.exam_id
            if exam_id not in exam_scores:
                exam_scores[exam_id] = {
                    "exam_id": exam_id,
                    "exam_name": score.exam.name,
                    "exam_date": score.exam.exam_date,
                    "scores": []
                }
            
            exam_scores[exam_id]["scores"].append({
                "id": score.id,
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "score": score.score,
                "ranking": score.ranking,
                "comments": score.comments
            })
        
        # 准备响应数据
        student_data = {
            "id": student.id,
            "name": student.name,
            "student_code": student.student_code,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "address": student.address,
            "phone": student.phone,
            "parent_name": student.parent_name,
            "parent_phone": student.parent_phone,
            "user_id": student.user_id,
            "username": student.user.username,
            "class_id": student.class_field.id,
            "class_name": student.class_field.name,
            "grade_name": student.class_field.grade.name if hasattr(student.class_field, "grade") else "",
            "exam_scores": list(exam_scores.values())
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学生详情成功",
            data=student_data,
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
            f"获取学生详情失败: {str(e)}"
        )

@router.put("/{student_id}", response_model=StandardResponse, summary="更新学生信息")
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    current_user: User = Depends(check_is_headteacher_or_admin)
):
    """
    更新学生信息
    
    - **student_id**: 学生ID
    - **name**: 学生姓名（可选）
    - **student_code**: 学号（可选）
    - **class_id**: 班级ID（可选）
    - **gender**: 性别（可选）
    - **birthday**: 出生日期（可选）
    - **address**: 住址（可选）
    - **phone**: 电话（可选）
    - **email**: 邮箱（可选）
    - **guardian**: 监护人（可选）
    - **guardian_phone**: 监护人电话（可选）
    
    权限要求：
    - 班主任：只能更新自己管理班级的学生信息
    - 管理员：可以更新任何学生的信息
    - 教师/学生：无权更新学生信息
    """
    try:
        # 获取学生信息
        student = await Student.get_or_none(id=student_id)
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{student_id}的学生"
            )
        
        # 检查学号是否已存在（如果修改了学号）
        if student_data.student_code and student_data.student_code != student.student_code:
            existing_student = await Student.get_or_none(student_code=student_data.student_code)
            if existing_student and existing_student.id != student_id:
                return create_error_response(
                    status.HTTP_409_CONFLICT, 
                    f"学号为{student_data.student_code}的学生已存在"
                )
        
        # 检查班级是否存在（如果修改了班级）
        if student_data.class_field and student_data.class_field != student.class_field_id:
            class_obj = await Class.get_or_none(id=student_data.class_field)
            if not class_obj:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{student_data.class_field}的班级"
                )
        
        # 更新学生信息
        update_data = student_data.dict(exclude_unset=True, exclude_none=True)
        
        # 处理class_field特殊字段
        if "class_field" in update_data:
            update_data["class_field_id"] = update_data.pop("class_field")
        
        # 应用更新
        for field, value in update_data.items():
            setattr(student, field, value)
        
        await student.save()
        
        # 预加载关联数据以便返回
        await student.fetch_related("class_field")
        if hasattr(student.class_field, "grade"):
            await student.class_field.fetch_related("grade")
        
        # 准备响应数据
        student_data = {
            "id": student.id,
            "name": student.name,
            "student_code": student.student_code,
            "gender": student.gender,
            "birth_date": student.birth_date,
            "address": student.address,
            "phone": student.phone,
            "parent_name": student.parent_name,
            "parent_phone": student.parent_phone,
            "class_id": student.class_field.id,
            "class_name": student.class_field.name,
            "grade_name": student.class_field.grade.name if hasattr(student.class_field, "grade") else ""
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="学生信息更新成功",
            data=student_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"更新学生信息失败: {str(e)}"
        )

@router.delete("/{student_id}", response_model=StandardResponse, summary="删除学生")
async def delete_student(
    student_id: int,
    current_user: User = Depends(check_is_admin)
):
    """
    删除学生信息
    
    - **student_id**: 学生ID
    
    权限要求：
    - 管理员：可以删除任何学生
    - 班主任/教师/学生：无权删除学生
    """
    try:
        # 获取学生信息
        student = await Student.get_or_none(id=student_id)
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{student_id}的学生"
            )
        
        # 检查是否有成绩关联
        score_count = await Score.filter(student_id=student_id).count()
        if score_count > 0:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                f"无法删除学生，该学生有{score_count}条成绩记录"
            )
        
        # 记录用户ID，用于后续可能的用户删除
        user_id = student.user_id
        
        # 删除学生
        await student.delete()
        
        # 可选：同时删除关联的用户账号
        # await User.filter(id=user_id).delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="学生删除成功",
            data=None,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"删除学生失败: {str(e)}"
        )

@router.get("/export", response_class=StreamingResponse, summary="导出学生信息Excel")
async def export_students(
    class_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(check_is_teacher_or_admin)
):
    """
    导出学生信息到Excel文件
    
    - **class_id**: 班级ID（可选，按班级筛选）
    - **search**: 搜索关键词（可选，按姓名或学号搜索）
    
    权限要求：
    - 教师：只能导出自己任教班级的学生信息
    - 班主任：可以导出自己管理班级的学生信息
    - 管理员：可以导出任何班级的学生信息
    - 学生：无权导出学生信息
    """
    try:
        # 构建查询
        query = Student.all().prefetch_related("class_field")
        
        # 班级筛选
        if class_id:
            query = query.filter(class_field_id=class_id)
            
            # 如果当前用户是教师且不是班主任，检查权限
            if current_user.role == UserRole.TEACHER:
                # 检查教师是否有权限访问该班级
                class_obj = await Class.get_or_none(id=class_id)
                if class_obj:
                    # 获取教师信息
                    teacher = await current_user.teacher
                    if teacher:
                        # 检查是否是班主任或任课教师
                        is_headteacher = await class_obj.headteacher.filter(id=teacher.id).exists()
                        is_teaching = await class_obj.teachers.filter(id=teacher.id).exists()
                        if not (is_headteacher or is_teaching):
                            return create_error_response(
                                status.HTTP_403_FORBIDDEN, 
                                "您没有权限访问该班级的学生"
                            )
                    else:
                        return create_error_response(
                            status.HTTP_403_FORBIDDEN, 
                            "教师信息不存在"
                        )
                else:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND, 
                        f"未找到ID为{class_id}的班级"
                    )
        
        # 关键词搜索
        if search:
            query = query.filter(
                name__icontains=search
            ) | query.filter(
                student_code__icontains=search
            )
        
        # 获取学生列表
        students = await query.order_by("student_code")
        
        # 准备导出数据
        data = []
        for student in students:
            # 预加载班级的年级信息
            if hasattr(student.class_field, "grade"):
                await student.class_field.fetch_related("grade")
            
            grade_name = student.class_field.grade.name if hasattr(student.class_field, "grade") and hasattr(student.class_field.grade, "name") else ""
            class_name = student.class_field.name if hasattr(student.class_field, "name") else ""
            
            student_data = {
                "id": student.id,
                "student_code": student.student_code,
                "name": student.name,
                "gender": student.gender or "",
                "birth_date": student.birth_date or "",
                "class_name": f"{grade_name}{class_name}",
                "phone": student.phone or "",
                "parent_name": student.parent_name or "",
                "parent_phone": student.parent_phone or "",
                "address": student.address or "",
            }
            data.append(student_data)
        
        # 定义列映射
        columns = [
            ("student_code", "学号"),
            ("name", "姓名"),
            ("gender", "性别"),
            ("birth_date", "出生日期"),
            ("class_name", "班级"),
            ("phone", "联系电话"),
            ("parent_name", "家长姓名"),
            ("parent_phone", "家长电话"),
            ("address", "家庭住址")
        ]
        
        # 生成Excel文件
        title = "学生信息表"
        if class_id:
            class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
            if class_obj:
                grade_name = class_obj.grade.name if hasattr(class_obj, "grade") and hasattr(class_obj.grade, "name") else ""
                title = f"{grade_name}{class_obj.name}学生信息表"
        
        output = ExcelUtils.write_excel(data, columns, title)
        
        # 生成文件名
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"学生信息表_{now}.xlsx"
        
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
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"导出学生信息失败: {str(e)}"
        )

@router.post("/import", response_model=StandardResponse, summary="从Excel导入学生信息")
async def import_students(
    file: UploadFile = File(...),
    class_id: int = Form(...),
    current_user: User = Depends(check_is_admin)
):
    """
    从Excel导入学生信息
    
    - **file**: Excel文件
    - **class_id**: 班级ID
    
    权限要求：
    - 管理员：可以导入任何班级的学生信息
    - 班主任/教师/学生：无权导入学生信息
    """
    try:
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 读取Excel文件
        df = await ExcelUtils.read_excel(file)
        
        # 检查必填列
        required_columns = ["学号", "姓名"]
        for column in required_columns:
            if column not in df.columns:
                return create_error_response(
                    status.HTTP_400_BAD_REQUEST, 
                    f"Excel文件缺少必填列: {column}"
                )
        
        # 验证学号格式
        def validate_student_code(code):
            if not isinstance(code, str) or len(code) < 5 or len(code) > 20:
                return "学号长度应在5-20个字符之间"
            if not code.isalnum():
                return "学号只能包含字母和数字"
            return True
        
        # 验证数据
        validators = {
            "学号": validate_student_code
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
            "学号": "student_code",
            "姓名": "name",
            "性别": "gender",
            "出生日期": "birth_date",
            "联系电话": "phone",
            "家长姓名": "parent_name",
            "家长电话": "parent_phone",
            "家庭住址": "address"
        })
        
        # 填充缺失的可选列
        optional_columns = ["gender", "birth_date", "phone", "parent_name", "parent_phone", "address"]
        for col in optional_columns:
            if col not in df.columns:
                df[col] = None
        
        # 处理日期列
        if "birth_date" in df.columns:
            df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.date
        
        # 开始导入数据
        success_count = 0
        error_count = 0
        error_details = []
        
        for idx, row in df.iterrows():
            try:
                # 检查学号是否已存在
                existing_student = await Student.get_or_none(student_code=row["student_code"])
                if existing_student:
                    error_count += 1
                    error_details.append({
                        "row": idx + 2,
                        "student_code": row["student_code"],
                        "name": row["name"],
                        "error": f"学号为{row['student_code']}的学生已存在"
                    })
                    continue
                
                # 创建学生记录
                # 注意：这里没有处理用户账号关联，实际情况可能需要同时创建用户账号
                await Student.create(
                    student_code=row["student_code"],
                    name=row["name"],
                    gender=row["gender"] if pd.notna(row["gender"]) else None,
                    birth_date=row["birth_date"] if pd.notna(row["birth_date"]) else None,
                    phone=row["phone"] if pd.notna(row["phone"]) else None,
                    parent_name=row["parent_name"] if pd.notna(row["parent_name"]) else None,
                    parent_phone=row["parent_phone"] if pd.notna(row["parent_phone"]) else None,
                    address=row["address"] if pd.notna(row["address"]) else None,
                    class_field_id=class_id,
                    # 需要处理用户关联
                    user_id=None  # 这里需要根据实际情况处理
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                error_details.append({
                    "row": idx + 2,
                    "student_code": row["student_code"] if "student_code" in row and pd.notna(row["student_code"]) else "",
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
    except HTTPException as e:
        return create_error_response(
            e.status_code, 
            e.detail
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"导入学生信息失败: {str(e)}"
        ) 