from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import pandas as pd
import urllib.parse

from app.api.dependencies.auth import get_current_user, get_current_active_user
from app.api.dependencies.permissions import (
    check_is_admin, check_is_teacher_or_admin, check_is_headteacher_or_admin,
    check_student_access, check_class_access, check_score_access
)
from app.core.config import settings
from app.models.enums import UserRole
from app.models.user import User
from app.models.score import Score
from app.models.student import Student
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.class_model import Class
from app.schemas.score import (
    ScoreCreate, ScoreUpdate, ScoreInExam, 
    StudentScoreResponse, Score_Pydantic
)
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

@router.post("/", response_model=StandardResponse, summary="创建学生成绩")
async def create_score(
    score_in: ScoreCreate,
    current_user: User = Depends(check_is_teacher_or_admin)
):
    """
    创建学生成绩
    
    - **student_id**: 学生ID
    - **exam_id**: 考试ID
    - **subject_id**: 学科ID
    - **score**: 分数
    - **ranking**: 排名（可选）
    - **comment**: 评语（可选）
    
    权限要求：
    - 教师：只能为自己教授的班级和学科添加成绩
    - 班主任：可以为自己所管理班级的学生添加任何学科的成绩
    - 管理员：可以添加任何学生的成绩
    - 学生：无权添加成绩
    """
    try:
        # 检查学生是否存在
        student = await Student.get_or_none(id=score_in.student_id)
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{score_in.student_id}的学生"
            )
        
        # 检查学科是否存在
        subject = await Subject.get_or_none(id=score_in.subject_id)
        if not subject:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{score_in.subject_id}的学科"
            )
        
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=score_in.exam_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{score_in.exam_id}的考试"
            )
        
        # 如果不是管理员，检查当前教师是否有权限录入该学生的成绩
        if current_user.role == UserRole.TEACHER:
            # 获取教师信息
            teacher = await Teacher.get_or_none(user_id=current_user.id)
            if not teacher:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "未找到对应的教师信息"
                )
                
            # 检查教师是否教授该学科
            if teacher.subject_id != score_in.subject_id:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "您只能录入自己任教学科的成绩"
                )
                
            # 检查学生是否在教师任教的班级中
            teacher_classes = await Class.filter(teachers__id=teacher.id)
            if not any(cls.id == student.class_field_id for cls in teacher_classes):
                return create_error_response(
                    status.HTTP_403_FORBIDDEN, 
                    "您只能录入自己任教班级学生的成绩"
                )
        
        # 检查成绩是否已存在
        existing_score = await Score.get_or_none(
            student_id=score_in.student_id,
            subject_id=score_in.subject_id,
            exam_id=score_in.exam_id
        )
        
        if existing_score:
            return create_error_response(
                status.HTTP_409_CONFLICT, 
                "该学生在此考试的这门学科已有成绩记录"
            )
        
        # 创建成绩
        score = await Score.create(
            student_id=score_in.student_id,
            subject_id=score_in.subject_id,
            exam_id=score_in.exam_id,
            score=score_in.score,
            ranking=score_in.ranking,
            comments=score_in.comments
        )
        
        # 转换为Pydantic模型
        score_data = await Score_Pydantic.from_tortoise_orm(score)
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="成绩创建成功",
            data=score_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            f"创建成绩失败: {str(e)}"
        )

@router.put("/{score_id}", response_model=StandardResponse, summary="更新学生成绩")
async def update_score(
    score_id: int,
    score_in: ScoreUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    更新学生成绩
    
    - **score_id**: 成绩ID
    - **score_in**: 更新的成绩数据
    
    权限要求：
    - 教师：可以更新自己任教班级学生的成绩
    - 班主任：可以更新自己管理班级学生的成绩
    - 管理员：可以更新任何学生的成绩
    - 学生：不允许更新任何成绩
    """
    try:
        # 检查成绩是否存在
        score = await Score.get_or_none(id=score_id)
        if not score:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{score_id}的成绩记录"
            )
        
        # 检查用户是否有权限修改该成绩
        await check_score_access(score_id, current_user)
        
        # 管理员或者任课教师才能修改成绩
        if current_user.role != UserRole.ADMIN and current_user.role != UserRole.TEACHER:
            return create_error_response(
                status.HTTP_403_FORBIDDEN, 
                "只有管理员或任课教师才能修改成绩"
            )
        
        # 更新成绩
        update_data = score_in.dict(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            setattr(score, field, value)
            
        await score.save()
        
        # 转换为Pydantic模型
        score_data = await Score_Pydantic.from_tortoise_orm(score)
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="成绩更新成功",
            data=score_data,
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
            f"更新成绩失败: {str(e)}"
        )

@router.delete("/{score_id}", response_model=StandardResponse, summary="删除学生成绩")
async def delete_score(
    score_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    删除学生成绩
    
    - **score_id**: 成绩ID
    
    权限要求：
    - 教师：可以删除自己任教班级学生的成绩
    - 班主任：可以删除自己管理班级学生的成绩
    - 管理员：可以删除任何学生的成绩
    - 学生：不允许删除任何成绩
    """
    try:
        # 检查成绩是否存在
        score = await Score.get_or_none(id=score_id)
        if not score:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{score_id}的成绩记录"
            )
        
        # 检查用户是否有权限删除该成绩
        await check_score_access(score_id, current_user)
        
        # 只有管理员和任课教师才能删除成绩
        if current_user.role != UserRole.ADMIN and current_user.role != UserRole.TEACHER:
            return create_error_response(
                status.HTTP_403_FORBIDDEN, 
                "只有管理员或任课教师才能删除成绩"
            )
        
        # 删除成绩
        await score.delete()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="成绩删除成功",
            data=None,
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
            f"删除成绩失败: {str(e)}"
        )

@router.get("/student/{student_id}", response_model=StandardResponse, summary="获取学生成绩列表")
async def get_student_scores(
    student_id: int,
    exam_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学生成绩列表
    
    - **student_id**: 学生ID
    - **exam_id**: 考试ID（可选，按考试筛选）
    - **subject_id**: 学科ID（可选，按学科筛选）
    
    权限要求：
    - 学生：只能查看自己的成绩
    - 教师：只能查看自己教授的班级和学科的学生成绩
    - 班主任：可以查看自己管理班级的所有学生成绩
    - 管理员：可以查看任何学生的成绩
    """
    try:
        # 检查用户是否有权限访问该学生数据
        await check_student_access(student_id, current_user)
        
        # 检查学生是否存在
        student = await Student.get_or_none(id=student_id).prefetch_related("class_field")
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{student_id}的学生"
            )
        
        # 构建查询
        query = Score.filter(student_id=student_id)
        
        if exam_id:
            query = query.filter(exam_id=exam_id)
            
        if subject_id:
            query = query.filter(subject_id=subject_id)
        
        # 获取成绩并预加载关联数据
        scores = await query.prefetch_related("subject", "exam")
        
        # 准备响应数据
        score_list = []
        total_score = 0
        
        for score in scores:
            score_data = {
                "id": score.id,
                "score": score.score,
                "ranking": score.ranking,
                "comments": score.comments,
                "subject_name": score.subject.name,
                "exam_name": score.exam.name,
                "exam_date": score.exam.exam_date
            }
            score_list.append(score_data)
            total_score += score.score
        
        average_score = total_score / len(scores) if scores else 0
        
        response_data = {
            "student_id": student.id,
            "student_name": student.name,
            "student_code": student.student_code,
            "class_name": student.class_field.name if hasattr(student, "class_field") else "",
            "scores": score_list,
            "total_score": total_score,
            "average_score": average_score,
            "score_count": len(scores)
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学生成绩成功",
            data=response_data,
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
            f"获取学生成绩失败: {str(e)}"
        )

@router.get("/class/{class_id}", response_model=StandardResponse, summary="获取班级学生成绩列表")
async def get_class_scores(
    class_id: int,
    exam_id: int,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级学生成绩列表
    
    - **class_id**: 班级ID
    - **exam_id**: 考试ID
    - **subject_id**: 学科ID（可选，按学科筛选）
    
    权限要求：
    - 学生：只能查看自己所在班级的成绩，且需要班主任或管理员授权
    - 教师：只能查看自己教授的班级和学科的成绩
    - 班主任：可以查看自己管理班级的所有成绩
    - 管理员：可以查看任何班级的成绩
    """
    try:
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 获取班级学生
        students = await Student.filter(class_field_id=class_id)
        student_ids = [student.id for student in students]
        
        if not student_ids:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"该班级没有学生"
            )
        
        # 构建查询
        exam_ids = [exam_id]
        
        # 如果有exam_id字段，找出所有同一考试ID的考试记录
        if hasattr(exam, 'exam_id') and exam.exam_id:
            exam_records = await Exam.filter(exam_id=exam.exam_id)
            exam_ids = [e.id for e in exam_records]
        
        # 构建最终查询
        query = Score.filter(student_id__in=student_ids)
        
        if subject_id:
            # 如果指定了学科，只查询该学科的成绩
            query = query.filter(exam_id=exam_id, subject_id=subject_id)
        else:
            # 查询所有相关考试的成绩
            query = query.filter(exam_id__in=exam_ids)
        
        # 一次性查询所有成绩，预加载关联数据
        scores = await query.prefetch_related("student", "subject", "exam")
        
        # 创建学生字典，用于快速查找学生数据
        student_dict = {student.id: student for student in students}
        
        # 组织成绩数据
        score_list = []
        
        for score in scores:
            student = student_dict.get(score.student_id)
            if student:
                score_list.append({
                    "id": score.id,
                    "student_id": score.student_id,
                    "student_name": student.name,
                    "student_code": student.student_code,
                    "subject_id": score.subject_id,
                    "subject_name": score.subject.name,
                    "exam_id": score.exam_id,
                    "exam_name": score.exam.name,
                    "score": score.score,
                    "ranking": score.ranking,
                    "comments": score.comments
                })
            
        # 准备响应数据
        response_data = {
            "class_id": class_id,
            "class_name": class_obj.name,
            "exam_id": exam_id,
            "exam_name": exam.name,
            "total_students": len(students),
            "scores": score_list
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级学生成绩列表成功",
            data=response_data,
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
            f"获取班级学生成绩列表失败: {str(e)}"
        )

@router.get("/export/class/{class_id}", response_class=StreamingResponse, summary="导出班级或年级成绩Excel")
async def export_class_scores(
    class_id: int,
    exam_id: int,
    subject_id: Optional[int] = None,
    is_grade_export: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """
    导出班级或年级成绩Excel文件
    
    - **class_id**: 班级ID（如果is_grade_export=True，则表示班级所属年级的任意班级ID）
    - **exam_id**: 考试ID
    - **subject_id**: 学科ID（可选，按学科筛选）
    - **is_grade_export**: 是否导出整个年级成绩（仅管理员可用）
    
    权限要求：
    - 教师：只能导出自己教授的班级和学科的成绩
    - 班主任：可以导出自己管理班级的所有成绩
    - 管理员：可以导出任何班级的成绩，并且可以导出整个年级的成绩
    - 学生：无权导出班级成绩
    """
    try:
        # 检查是否要导出年级成绩
        if is_grade_export and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员才能导出年级成绩"
            )
        
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{class_id}的班级"
            )
        
        # 检查年级是否存在
        grade_id = class_obj.grade_id if hasattr(class_obj, "grade_id") and class_obj.grade_id else None
        if is_grade_export and not grade_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该班级没有关联的年级，无法导出年级成绩"
            )
        
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject")
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{exam_id}的考试"
            )
        
        # 确定相关的考试列表
        related_exams = [exam]
        if exam.exam_id:
            # 获取同一考试组的所有考试
            other_exams = await Exam.filter(exam_id=exam.exam_id).exclude(id=exam_id).prefetch_related("subject")
            related_exams.extend(other_exams)
        
        # 获取学科信息
        subjects_to_include = []
        if subject_id:
            # 如果指定了学科，只包含该学科
            for exam_obj in related_exams:
                if exam_obj.subject_id == subject_id:
                    subjects_to_include.append(exam_obj.subject)
                    break
            
            if not subjects_to_include:
                subject = await Subject.get_or_none(id=subject_id)
                if not subject:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"未找到ID为{subject_id}的学科"
                    )
                subjects_to_include = [subject]
        else:
            # 如果没有指定学科，包含考试组中的所有学科
            for exam_obj in related_exams:
                subjects_to_include.append(exam_obj.subject)
        
        # 确保subjects_to_include不是空列表
        if not subjects_to_include:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="没有找到与考试相关的学科"
            )
        
        # 根据是否导出年级成绩获取学生列表
        if is_grade_export and grade_id:
            # 获取年级内所有班级
            grade = await Class.get_or_none(id=class_obj.grade_id).prefetch_related("grade")
            grade_name = grade.grade.name if grade and hasattr(grade, "grade") and grade.grade else "未知年级"
            
            grade_classes = await Class.filter(grade_id=grade_id)
            grade_class_ids = [c.id for c in grade_classes]
            
            # 获取年级内所有学生并预加载班级数据
            students = await Student.filter(class_field_id__in=grade_class_ids).prefetch_related("class_field").order_by("class_field_id", "student_code")
        else:
            # 获取班级学生
            students = await Student.filter(class_field_id=class_id).order_by("student_code")
            grade_name = class_obj.grade.name if hasattr(class_obj, "grade") and class_obj.grade else ""
        
        # 创建用于存储每个考试的ID的映射
        exam_id_by_subject = {}
        for exam_obj in related_exams:
            exam_id_by_subject[exam_obj.subject_id] = exam_obj.id
        
        # 提前批量获取所有学生的所有成绩，减少数据库查询次数
        student_ids = [student.id for student in students]
        
        # 构建查询所需的考试ID列表
        exam_ids = list(exam_id_by_subject.values())
        
        # 批量获取所有相关成绩
        all_scores = await Score.filter(
            student_id__in=student_ids,
            exam_id__in=exam_ids,
            subject_id__in=[subject.id for subject in subjects_to_include]
        ).prefetch_related("subject")
        
        # 创建成绩查询索引，便于快速获取成绩
        # 格式: {(student_id, subject_id, exam_id): score_obj}
        score_lookup = {}
        for score in all_scores:
            score_lookup[(score.student_id, score.subject_id, score.exam_id)] = score
        
        # 创建成绩数据的DataFrame
        data = []
        student_dict = {student.id: student for student in students}  # 用于后续年级排名计算
        
        for student in students:
            # 创建学生行数据
            row = {
                "学号": student.student_code,
                "姓名": student.name,
            }
            
            # 如果是年级导出，添加班级信息
            if is_grade_export:
                row["班级"] = student.class_field.name if hasattr(student, "class_field") and student.class_field else ""
            
            # 添加总分和排名字段
            row["总分"] = 0
            row["班级排名"] = 0
            if is_grade_export:
                row["年级排名"] = 0
            
            # 获取各科目成绩
            valid_scores = 0
            for subject in subjects_to_include:
                # 获取该学科对应的考试ID
                subject_exam_id = exam_id_by_subject.get(subject.id, exam_id)
                
                # 从预加载的成绩中获取
                score = score_lookup.get((student.id, subject.id, subject_exam_id))
                
                # 如果有成绩，添加到总分，并记录单科成绩
                if score:
                    row[subject.name] = score.score
                    row["总分"] += score.score
                    valid_scores += 1
                else:
                    row[subject.name] = "缺考"
            
            data.append(row)
        
        # 创建DataFrame并排序
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(by=["总分"], ascending=False)
            
            # 按总分计算年级排名
            df["年级排名"] = df["总分"].rank(method='min', ascending=False).astype(int)
            
            # 如果是导出班级成绩，计算班级内排名
            if not is_grade_export:
                df["班级排名"] = df["总分"].rank(method='min', ascending=False).astype(int)
            else:
                # 按班级和总分分组计算班级内排名
                if "班级" in df.columns:
                    # 对每个班级分别计算排名
                    for class_name in df["班级"].unique():
                        class_mask = df["班级"] == class_name
                        df.loc[class_mask, "班级排名"] = df.loc[class_mask, "总分"].rank(method='min', ascending=False).astype(int)
        
        # 添加标题行
        if is_grade_export:
            # 获取年级名称，使用之前获取到的grade_name
            title = f"{grade_name} - {exam.name}年级成绩单"
        else:
            class_name = f"{class_obj.grade.name}{class_obj.name}" if hasattr(class_obj, "grade") and class_obj.grade else class_obj.name
            title = f"{class_name} - {exam.name}成绩单"
        
        # 创建Excel文件
        output = io.BytesIO()
        
        # 使用pandas直接导出到Excel，使用xlsxwriter引擎
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 写入数据
            df.to_excel(writer, sheet_name='成绩单', index=False, startrow=1)  # 从第2行开始写入数据，给标题留空间
            
            # 获取工作表
            workbook = writer.book
            worksheet = writer.sheets['成绩单']
            
            # 创建格式
            title_format = workbook.add_format({
                'bold': True, 
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': '微软雅黑',
                'border': 0
            })
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': '微软雅黑',
                'font_size': 11
            })
            
            # 创建数据单元格格式
            num_format = workbook.add_format({
                'num_format': '0.00',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑'
            })
            
            text_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑'
            })
            
            # 创建斑马线格式
            alt_row_format = workbook.add_format({
                'bg_color': '#E6F0FF',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑'
            })
            
            alt_row_num_format = workbook.add_format({
                'bg_color': '#E6F0FF',
                'num_format': '0.00',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑'
            })
            
            # 创建总分和平均分格式
            total_format = workbook.add_format({
                'bold': True,
                'num_format': '0.00',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑',
                'bg_color': '#FFEB9C'
            })
            
            alt_total_format = workbook.add_format({
                'bold': True,
                'num_format': '0.00',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'font_name': '微软雅黑',
                'bg_color': '#FFC000'
            })
            
            # 创建排名格式
            rank_format = workbook.add_format({
                'bold': True,
                'bg_color': '#BDD7EE',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': '微软雅黑'
            })
            
            alt_rank_format = workbook.add_format({
                'bold': True,
                'bg_color': '#8EA9DB',
                'border': 1,
                'align': 'center', 
                'valign': 'vcenter',
                'font_name': '微软雅黑'
            })
            
            # 创建班级列格式
            class_format = workbook.add_format({
                'bold': True,
                'bg_color': '#C6E0B4',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': '微软雅黑'
            })
            
            alt_class_format = workbook.add_format({
                'bold': True,
                'bg_color': '#A9D08E',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': '微软雅黑'
            })
            
            # 计算总列数并生成对应的列字母
            total_columns = len(df.columns)
            last_col_letter = chr(ord('A') + total_columns - 1)
            
            # 添加标题 - 使用正确的列数
            worksheet.merge_range(f'A1:{last_col_letter}1', title, title_format)
            
            # 设置表头格式
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(1, col_num, value, header_format)
            
            # 设置单元格格式和斑马线
            for row_num, row in enumerate(df.iterrows(), start=2):  # 数据从第3行开始
                # 判断是否为偶数行，应用斑马线效果
                is_even_row = row_num % 2 == 0
                
                for col_num, (column, value) in enumerate(row[1].items()):
                    # 为"总分"列应用特殊格式
                    if column == "总分":
                        cell_format = total_format if is_even_row else alt_total_format
                    # 为排名列应用特殊格式 
                    elif column in ["班级排名", "年级排名"]:
                        cell_format = rank_format if is_even_row else alt_rank_format
                    # 为班级列应用特殊格式
                    elif column == "班级":
                        cell_format = class_format if is_even_row else alt_class_format
                    # 为数字类型应用数字格式
                    elif isinstance(value, (int, float)):
                        cell_format = num_format if is_even_row else alt_row_num_format
                    # 为文本应用文本格式
                    else:
                        cell_format = text_format if is_even_row else alt_row_format
                    
                    worksheet.write(row_num, col_num, value, cell_format)
            
            # 调整列宽
            for i, col in enumerate(df.columns):
                # 数学列特别处理，强制设置较宽的宽度
                if col == "数学":
                    worksheet.set_column(i, i, 15)
                    continue
                    
                # 计算最大宽度
                header_width = len(str(col)) * 1.2  # 考虑中文字符宽度
                max_data_width = 0
                
                # 检查数据宽度
                for value in df[col].astype(str):
                    # 计算字符串宽度，中文字符算两个宽度
                    width = sum(2 if ord(c) > 127 else 1 for c in str(value)) * 1.1
                    max_data_width = max(max_data_width, width)
                
                column_width = max(header_width, max_data_width)
                
                # 确保列宽不小于最小值
                min_width = 10 if col in ["学号", "姓名", "班级", "班级排名", "年级排名"] else 8
                column_width = max(column_width, min_width)
                
                worksheet.set_column(i, i, min(column_width, 25))  # 最大宽度限制为25
            
            # 设置行高
            worksheet.set_row(0, 30)  # 标题行高
            worksheet.set_row(1, 20)  # 表头行高
            
            # 为所有数据行设置行高
            for i in range(2, len(df) + 2):
                worksheet.set_row(i, 18)
                
            # 冻结表头
            worksheet.freeze_panes(2, 0)
        
        # 重置输出流位置
        output.seek(0)
        
        # 生成文件名
        if is_grade_export:
            # 使用之前获取到的grade_name
            filename = f"{grade_name}_{exam.name}_年级成绩单.xlsx"
        else:
            class_name = f"{class_obj.grade.name}{class_obj.name}" if hasattr(class_obj, "grade") and class_obj.grade else class_obj.name
            filename = f"{class_name}_{exam.name}_成绩单.xlsx"
        encoded_filename = urllib.parse.quote(filename)
        
        # 返回Excel文件
        headers = {
            "Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded_filename}',
        }
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出成绩单失败: {str(e)}"
        )

@router.post("/import", response_model=StandardResponse, summary="从Excel导入成绩")
async def import_scores(
    file: UploadFile = File(...),
    exam_id: int = Form(...),
    class_id: int = Form(...),
    subject_id: Optional[int] = Form(None),
    current_user: User = Depends(check_is_teacher_or_admin)
):
    """
    从Excel导入成绩
    
    - **file**: Excel文件
    - **exam_id**: 考试ID
    - **class_id**: 班级ID
    - **subject_id**: 学科ID（可选）
    
    权限要求：
    - 教师：只能导入自己教授的班级和学科的成绩
    - 班主任：可以导入自己管理班级的所有成绩
    - 管理员：可以导入任何班级的成绩
    - 学生：无权导入成绩
    """
    try:
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject")
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id)
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查教师权限
        if current_user.role == UserRole.TEACHER:
            teacher = await current_user.teacher
            if teacher:
                # 检查是否有权限访问该班级
                is_teaching = await class_obj.teachers.filter(id=teacher.id).exists()
                is_headteacher = class_obj.headteacher_id == teacher.id
                
                if not (is_teaching or is_headteacher):
                    return create_error_response(
                        status.HTTP_403_FORBIDDEN,
                        "您没有权限为该班级导入成绩"
                    )
                
                # 如果提供了学科ID，检查教师是否教授该学科
                if subject_id and teacher.subject_id != subject_id:
                    return create_error_response(
                        status.HTTP_403_FORBIDDEN,
                        "您只能导入自己教授学科的成绩"
                    )
            else:
                return create_error_response(
                    status.HTTP_403_FORBIDDEN,
                    "无法获取教师信息"
                )
        
        # 检查学科ID，确定要导入的考试
        target_exam = exam
        if subject_id:
            # 如果指定了学科ID，检查考试组中是否有该学科的考试
            if exam.subject_id != subject_id and exam.exam_id:
                # 查找同一考试组中的对应学科考试
                target_exam = await Exam.filter(exam_id=exam.exam_id, subject_id=subject_id).first()
                
                if not target_exam:
                    # 如果考试组中没有该学科的考试，检查学科是否存在
                    subject = await Subject.get_or_none(id=subject_id)
                    if not subject:
                        return create_error_response(
                            status.HTTP_404_NOT_FOUND,
                            f"未找到ID为{subject_id}的学科"
                        )
                    
                    # 创建该学科的考试记录
                    target_exam = await Exam.create(
                        name=exam.name,
                        exam_date=exam.exam_date,
                        subject_id=subject_id,
                        total_score=100.0,  # 默认总分
                        description=f"{exam.description} - {subject.name}",
                        exam_id=exam.exam_id or f"exam_group_{exam.id}"  # 创建考试组ID
                    )
                    
                    # 如果原考试没有exam_id，更新它
                    if not exam.exam_id:
                        exam.exam_id = target_exam.exam_id
                        await exam.save()
        
        # 读取Excel文件
        try:
            df = pd.read_excel(file.file.read())
        except Exception as e:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                f"无法读取Excel文件: {str(e)}"
            )
        
        # 验证必填列
        required_columns = ["学号", "姓名", "分数"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST,
                f"Excel文件缺少必填列: {', '.join(missing_columns)}"
            )
        
        # 验证分数列是否有效
        def validate_score(score):
            if pd.isna(score):
                return "分数不能为空"
            try:
                float_score = float(score)
                if float_score < 0 or float_score > target_exam.total_score:
                    return f"分数应在0-{target_exam.total_score}之间"
            except ValueError:
                return "分数应为数字"
            return True
        
        # 验证数据
        df["验证"] = df["分数"].apply(validate_score)
        invalid_rows = df[df["验证"] != True]
        
        if not invalid_rows.empty:
            errors = []
            for index, row in invalid_rows.iterrows():
                errors.append({
                    "row": index + 2,  # Excel行从1开始，标题行为1
                    "student_code": row["学号"],
                    "name": row["姓名"],
                    "error": row["验证"]
                })
            
            return StandardResponse(
                code=status.HTTP_400_BAD_REQUEST,
                message="成绩数据验证失败",
                data={"errors": errors},
                timestamp=datetime.now()
            )
        
        # 获取班级学生
        students = await Student.filter(class_field_id=class_id)
        student_dict = {student.student_code: student for student in students}
        
        # 导入成绩
        success_count = 0
        error_count = 0
        error_details = []
        
        for index, row in df.iterrows():
            try:
                student_code = str(row["学号"])
                student = student_dict.get(student_code)
                
                if not student:
                    error_count += 1
                    error_details.append({
                        "row": index + 2,
                        "student_code": student_code,
                        "name": row["姓名"],
                        "error": "学号不存在或不属于该班级"
                    })
                    continue
                
                # 检查成绩是否已存在
                existing_score = await Score.filter(
                    student_id=student.id,
                    exam_id=target_exam.id,
                    subject_id=target_exam.subject_id
                ).first()
                
                score_value = float(row["分数"])
                comments = row.get("评语", "") if "评语" in row else None
                
                if existing_score:
                    # 更新现有成绩
                    existing_score.score = score_value
                    if comments is not None:
                        existing_score.comments = comments
                    await existing_score.save()
                else:
                    # 创建新成绩
                    await Score.create(
                        student_id=student.id,
                        exam_id=target_exam.id,
                        subject_id=target_exam.subject_id,
                        score=score_value,
                        comments=comments
                    )
                
                success_count += 1
            except Exception as e:
                error_count += 1
                error_details.append({
                    "row": index + 2,
                    "student_code": row.get("学号", ""),
                    "name": row.get("姓名", ""),
                    "error": str(e)
                })
        
        # 计算排名
        if success_count > 0:
            # 获取该考试该科目的所有成绩
            scores = await Score.filter(
                exam_id=target_exam.id,
                subject_id=target_exam.subject_id
            ).order_by("-score")
            
            # 计算排名
            current_rank = 1
            current_score = None
            for i, score in enumerate(scores):
                if current_score != score.score:
                    current_rank = i + 1
                    current_score = score.score
                score.ranking = current_rank
                await score.save()
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message=f"成绩导入完成，成功{success_count}条，失败{error_count}条",
            data={
                "success_count": success_count,
                "error_count": error_count,
                "error_details": error_details
            },
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"导入成绩失败: {str(e)}"
        )

@router.get("/import/template", response_class=StreamingResponse, summary="获取成绩导入模板")
async def get_score_import_template(
    class_id: int,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取成绩导入模板Excel
    
    - **class_id**: 班级ID
    - **subject_id**: 学科ID（可选）
    
    权限要求：
    - 教师：只能获取自己任教班级和学科的导入模板
    - 班主任：可以获取自己管理班级的任何学科的导入模板
    - 管理员：可以获取任何班级和学科的导入模板
    - 学生：无权获取导入模板
    """
    try:
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
        if not class_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{class_id}的班级"
            )
        
        # 检查用户权限
        if current_user.role == UserRole.TEACHER:
            teacher = await current_user.teacher
            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="未找到对应的教师信息"
                )
                
            # 检查是否为该班级的任课教师或班主任
            is_headteacher = class_obj.headteacher_id == teacher.id
            is_teaching = await teacher.teaching_classes.filter(id=class_id).exists()
            
            if not (is_headteacher or is_teaching):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您不是该班级的任课教师或班主任，无权获取导入模板"
                )
                
            # 如果指定了学科，检查是否教授该学科
            if subject_id and teacher.subject_id != subject_id and not is_headteacher:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您只能获取自己任教学科的导入模板"
                )
        elif current_user.role == UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="学生无权获取成绩导入模板"
            )
        
        # 获取班级学生
        students = await Student.filter(class_field_id=class_id).order_by("student_code")
        
        # 准备模板数据
        data = []
        for student in students:
            student_data = {
                "学号": student.student_code,
                "姓名": student.name,
                "分数": "",
                "评语": ""
            }
            data.append(student_data)
        
        # 定义列
        columns = [
            ("学号", "学号"),
            ("姓名", "姓名"),
            ("分数", "分数"),
            ("评语", "评语")
        ]
        
        # 生成Excel文件
        grade_name = class_obj.grade.name if hasattr(class_obj, "grade") and class_obj.grade else ""
        class_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
        
        title = f"{class_name}成绩导入模板"
        if subject_id:
            subject = await Subject.get_or_none(id=subject_id)
            if subject:
                title = f"{class_name}{subject.name}成绩导入模板"
        
        output = ExcelUtils.write_excel(data, columns, title)
        
        # 生成文件名
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"成绩导入模板_{now}.xlsx"
        
        # 返回Excel文件
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        return StreamingResponse(
            output, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取成绩导入模板失败: {str(e)}"
        ) 