from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import io
from fastapi.responses import StreamingResponse

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.permissions import (
    check_is_admin, check_is_teacher_or_admin,
    check_student_access, check_class_access
)
from app.models.user import User
from app.models.score import Score
from app.models.student import Student
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.class_model import Class
from app.models.grade import Grade
from app.models.analytics import AnalysisTask, AnalysisReport, AnalysisSnapshot, AnalysisTaskStatus
from app.schemas.analytics import (
    AnalysisTaskCreate, AnalysisTaskResponse, ClassBenchmarkData,
    StudentTrendData, ComparativeAnalysisData, ExportRequest,
    AnalysisTaskType, AnalysisReportFormat
)
from app.schemas.common import StandardResponse
from app.utils.excel_utils import ExcelUtils

router = APIRouter()

# 创建标准错误响应
def create_error_response(status_code: int, detail: str) -> StandardResponse:
    """创建标准错误响应"""
    return StandardResponse(
        code=status_code,
        message=detail,
        data=None,
        timestamp=datetime.now()
    )

# 创建分析任务
@router.post("/tasks", response_model=StandardResponse, summary="创建分析任务")
async def create_analysis_task(
    task: AnalysisTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    创建分析任务
    
    - **task_type**: 任务类型 (class_benchmark, student_trend, comparative, comprehensive)
    - **target_ids**: 目标ID列表 (学生/班级/年级ID)
    - **subject_ids**: 学科ID列表 (可选)
    - **exam_ids**: 考试ID列表 (可选)
    - **time_range**: 时间范围 (可选)
    - **parameters**: 附加参数 (可选)
    
    权限要求：
    - 学生：只能对自己创建分析任务
    - 教师：可以对自己任教的班级和学科创建分析任务
    - 班主任：可以对自己管理的班级创建任何分析任务
    - 管理员：可以创建任何分析任务
    """
    try:
        # 验证目标存在
        if task.task_type == AnalysisTaskType.STUDENT_TREND:
            for student_id in task.target_ids:
                await check_student_access(student_id, current_user)
                student = await Student.get_or_none(id=student_id)
                if not student:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND,
                        f"未找到ID为{student_id}的学生"
                    )
        elif task.task_type == AnalysisTaskType.CLASS_BENCHMARK:
            for class_id in task.target_ids:
                await check_class_access(class_id, current_user)
                class_obj = await Class.get_or_none(id=class_id)
                if not class_obj:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND,
                        f"未找到ID为{class_id}的班级"
                    )
                    
        # 创建任务记录
        analysis_task = await AnalysisTask.create(
            task_type=task.task_type,
            user=current_user,
            status="pending",
            progress=0,
            parameters={
                "target_ids": task.target_ids,
                "subject_ids": task.subject_ids,
                "exam_ids": task.exam_ids,
                "time_range": {k: v.isoformat() for k, v in task.time_range.items()} if task.time_range else None,
                "parameters": task.parameters
            }
        )
        
        # 在后台处理任务
        background_tasks.add_task(process_analysis_task, analysis_task.id)
        
        return StandardResponse(
            code=status.HTTP_201_CREATED,
            message="分析任务创建成功",
            data={"task_id": analysis_task.id},
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(e.status_code, e.detail)
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"创建分析任务失败: {str(e)}"
        )

# 获取分析任务列表
@router.get("/tasks", response_model=StandardResponse, summary="获取分析任务列表")
async def get_analysis_tasks(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(20, gt=0, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取分析任务列表
    
    - **task_type**: 任务类型过滤 (可选)
    - **status**: 任务状态过滤 (可选)
    - **page**: 页码
    - **limit**: 每页条数
    
    权限要求：
    - 所有用户：只能查看自己创建的分析任务列表
    - 管理员：可以查看所有用户创建的分析任务
    """
    try:
        # 构建查询
        query = AnalysisTask.filter(user=current_user)
        
        if task_type:
            query = query.filter(task_type=task_type)
            
        if status:
            query = query.filter(status=status)
            
        # 计算总数
        total = await query.count()
        
        # 分页查询
        tasks = await query.order_by("-created_at").offset((page - 1) * limit).limit(limit)
        
        # 格式化响应
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "results": task.results
            })
            
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取分析任务列表成功",
            data={
                "items": task_list,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            },
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取分析任务列表失败: {str(e)}"
        )

# 获取分析任务详情
@router.get("/tasks/{task_id}", response_model=StandardResponse, summary="获取分析任务详情")
async def get_analysis_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取分析任务详情
    
    - **task_id**: 任务ID
    
    权限要求：
    - 所有用户：只能查看自己创建的分析任务
    - 管理员：可以查看任何分析任务详情
    """
    try:
        # 查询任务
        task = await AnalysisTask.get_or_none(id=task_id)
        
        if not task:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到ID为{task_id}的分析任务"
            )
            
        # 检查权限
        if task.user_id != current_user.id and current_user.role not in ["admin"]:
            return create_error_response(
                status.HTTP_403_FORBIDDEN,
                "您没有权限查看此分析任务"
            )
            
        # 格式化响应
        task_data = {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "parameters": task.parameters,
            "results": task.results
        }
        
        # 获取关联的报告
        reports = await AnalysisReport.filter(task_id=task.id)
        report_list = []
        
        for report in reports:
            report_list.append({
                "id": report.id,
                "report_type": report.report_type,
                "title": report.title,
                "format": report.format,
                "file_path": report.file_path,
                "size": report.size,
                "is_public": report.is_public,
                "created_at": report.created_at
            })
            
        task_data["reports"] = report_list
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取分析任务详情成功",
            data=task_data,
            timestamp=datetime.now()
        )
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取分析任务详情失败: {str(e)}"
        )

# 学生成绩趋势分析
@router.get("/student/{student_id}/trend", response_model=StandardResponse, summary="获取学生成绩趋势分析")
async def get_student_trend(
    student_id: int,
    subject_id: Optional[int] = None,
    limit: int = Query(10, description="最大记录数"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学生成绩趋势分析
    
    - **student_id**: 学生ID
    - **subject_id**: 学科ID (可选)
    - **limit**: 最大记录数（默认10）
    
    权限要求：
    - 学生：只能查看自己的成绩趋势
    - 教师：可以查看自己任教班级学生的成绩趋势
    - 班主任：可以查看自己管理班级所有学生的成绩趋势
    - 管理员：可以查看任何学生的成绩趋势
    """
    try:
        # 检查权限
        await check_student_access(student_id, current_user)
        
        # 获取学生信息
        student = await Student.get_or_none(id=student_id).prefetch_related("class_field")
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到ID为{student_id}的学生"
            )
            
        # 获取班级信息和年级信息
        class_id = student.class_field_id
        grade_id = None
        if student.class_field and hasattr(student.class_field, "grade_id"):
            grade_id = student.class_field.grade_id
            
        # 构建查询
        query = Score.filter(student_id=student_id)
        if subject_id:
            query = query.filter(subject_id=subject_id)
            
        # 获取成绩并预加载关联数据
        scores = await query.prefetch_related("subject", "exam").order_by("-exam__exam_date").limit(limit)
        
        if not scores:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到该学生的成绩数据"
            )
            
        # 收集考试ID以获取排名历史
        exam_ids = [score.exam_id for score in scores]
        unique_exam_ids = list(set(exam_ids))
        
        # 创建DataFrame进行分析
        data = []
        for score in scores:
            data.append({
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "exam_id": score.exam_id,
                "exam_name": score.exam.name,
                "exam_date": score.exam.exam_date,
                "score": score.score,
                "ranking": score.ranking
            })
            
        df = pd.DataFrame(data)
        
        # 计算趋势数据
        trend_data = {
            "exam_labels": [],
            "series_data": {},
            "radar_data": {
                "indicators": [],
                "series_data": []
            }
        }
        
        # 处理每个学科的趋势
        subject_scores = {}
        
        if not df.empty:
            # 按学科和考试排序
            df_sorted = df.sort_values(["subject_name", "exam_date"])
            
            # 收集每个学科的所有成绩记录
            for subject_name, group in df_sorted.groupby("subject_name"):
                scores_list = []
                for _, row in group.iterrows():
                    scores_list.append({
                        "exam_id": row["exam_id"],
                        "exam_name": row["exam_name"],
                        "exam_date": row["exam_date"],
                        "score": row["score"],
                        "ranking": row["ranking"] if pd.notna(row["ranking"]) else None
                    })
                subject_scores[subject_name] = scores_list
                
                # 为每个考试添加数据点
                if subject_name not in trend_data["series_data"]:
                    trend_data["series_data"][subject_name] = []
                    
                for _, row in group.iterrows():
                    exam_name = row["exam_name"]
                    if exam_name not in trend_data["exam_labels"]:
                        trend_data["exam_labels"].append(exam_name)
                    trend_data["series_data"][subject_name].append(float(row["score"]))
                    
                # 添加雷达图指标
                if len(scores_list) > 0:
                    latest_score = scores_list[-1]["score"]
                    trend_data["radar_data"]["indicators"].append({
                        "name": subject_name,
                        "max": 100
                    })
                    trend_data["radar_data"]["series_data"].append(float(latest_score))
        
        # 新增：获取年级排名数据
        grade_ranks = {}
        dual_rank = None
        rank_history = []
        
        # 预先获取所需的数据，减少重复查询
        if grade_id:
            # 1. 一次性获取年级内所有班级
            grade_classes = await Class.filter(grade_id=grade_id)
            grade_class_ids = [c.id for c in grade_classes]
            
            # 2. 一次性获取年级内所有学生
            grade_students = await Student.filter(class_field_id__in=grade_class_ids)
            grade_student_ids = [s.id for s in grade_students]
            
            # 3. 一次性获取班级内所有学生
            class_students = await Student.filter(class_field_id=class_id)
            class_student_ids = [s.id for s in class_students]
            
            # 4. 如果数据不为空，继续处理排名数据
            if not df.empty and len(grade_student_ids) > 0:
                # 获取所有需要查询的科目和考试组合
                subject_exam_pairs = []
                for subject_name, subject_group in df_sorted.groupby("subject_name"):
                    if len(subject_group) > 0:
                        # 获取最新考试记录
                        latest_exam = subject_group.iloc[-1]
                        subject_exam_pairs.append((latest_exam["subject_id"], latest_exam["exam_id"]))
                
                # 批量获取所有需要的成绩数据
                all_subject_scores = {}
                if subject_exam_pairs:
                    for subject_id, exam_id in subject_exam_pairs:
                        # 查询该考试该学科的所有成绩
                        grade_scores = await Score.filter(
                            exam_id=exam_id,
                            subject_id=subject_id,
                            student_id__in=grade_student_ids
                        )
                        all_subject_scores[(subject_id, exam_id)] = grade_scores
                
                # 处理单科年级排名
                for subject_name, subject_group in df_sorted.groupby("subject_name"):
                    if len(subject_group) > 0:
                        latest_exam = subject_group.iloc[-1]
                        subject_id = latest_exam["subject_id"]
                        exam_id = latest_exam["exam_id"]
                        
                        grade_scores = all_subject_scores.get((subject_id, exam_id), [])
                        
                        if grade_scores:
                            # 创建DataFrame计算排名
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "score": s.score
                            } for s in grade_scores if s.score is not None])
                            
                            if not grade_df.empty:
                                # 对有效成绩进行排名（使用min方法确保并列排名）
                                grade_df["rank"] = grade_df["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生在年级中的排名
                                student_rank = grade_df[grade_df["student_id"] == student_id]
                                
                                if not student_rank.empty:
                                    rank = int(student_rank["rank"].iloc[0])
                                    total = len(grade_df)
                                    percentage = round(rank * 100 / total, 2)
                                    percentile = round(100 - percentage, 2)
                                    
                                    grade_ranks[subject_name] = {
                                        "absolute_rank": rank,
                                        "total_students": total,
                                        "percentage": percentage,
                                        "percentile": percentile
                                    }
            
                # 获取双维度排名数据
                if unique_exam_ids:
                    # 获取最近的一次考试
                    recent_exams = await Exam.filter(id__in=unique_exam_ids).order_by("-exam_date")
                    if recent_exams:
                        recent_exam = recent_exams[0]
                        
                        # 批量获取成绩数据
                        all_class_scores = await Score.filter(
                            exam_id=recent_exam.id,
                            student_id__in=class_student_ids
                        )
                        
                        all_grade_scores = await Score.filter(
                            exam_id=recent_exam.id,
                            student_id__in=grade_student_ids
                        )
                        
                        if all_class_scores and all_grade_scores:
                            # 创建DataFrame计算班级排名
                            class_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in all_class_scores if s.score is not None])
                            
                            # 创建DataFrame计算年级排名
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in all_grade_scores if s.score is not None])
                            
                            if not class_df.empty and not grade_df.empty:
                                # 计算每个学生的总分
                                class_totals = class_df.groupby("student_id")["score"].sum().reset_index()
                                grade_totals = grade_df.groupby("student_id")["score"].sum().reset_index()
                                
                                # 计算排名（使用min方法确保并列排名）
                                class_totals["rank"] = class_totals["score"].rank(method="min", ascending=False).astype(int)
                                grade_totals["rank"] = grade_totals["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生排名
                                student_class_rank = class_totals[class_totals["student_id"] == student_id]
                                student_grade_rank = grade_totals[grade_totals["student_id"] == student_id]
                                
                                if not student_class_rank.empty and not student_grade_rank.empty:
                                    class_rank = int(student_class_rank["rank"].iloc[0])
                                    class_total = len(class_totals)
                                    class_percentile = round(100 - (class_rank * 100 / class_total), 2)
                                    
                                    grade_rank = int(student_grade_rank["rank"].iloc[0])
                                    grade_total = len(grade_totals)
                                    grade_percentile = round(100 - (grade_rank * 100 / grade_total), 2)
                                    
                                    dual_rank = {
                                        "class_rank": class_rank,
                                        "class_total": class_total,
                                        "grade_rank": grade_rank,
                                        "grade_total": grade_total,
                                        "class_percentile": class_percentile,
                                        "grade_percentile": grade_percentile
                                    }
                
                # 获取排名历史
                if unique_exam_ids and len(class_student_ids) > 0 and len(grade_student_ids) > 0:
                    # 批量获取所有相关考试的数据
                    all_exams = await Exam.filter(id__in=unique_exam_ids).order_by("-exam_date")
                    
                    # 批量获取所有考试的班级和年级成绩
                    batch_class_scores = {}
                    batch_grade_scores = {}
                    
                    for exam in all_exams:
                        # 批量获取该考试的班级和年级成绩
                        class_scores = await Score.filter(
                            exam_id=exam.id,
                            student_id__in=class_student_ids
                        )
                        
                        grade_scores = await Score.filter(
                            exam_id=exam.id,
                            student_id__in=grade_student_ids
                        )
                        
                        batch_class_scores[exam.id] = class_scores
                        batch_grade_scores[exam.id] = grade_scores
                    
                    # 处理每个考试的排名数据
                    for exam in all_exams:
                        class_scores = batch_class_scores.get(exam.id, [])
                        grade_scores = batch_grade_scores.get(exam.id, [])
                        
                        if class_scores and grade_scores:
                            # 创建DataFrame
                            class_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in class_scores if s.score is not None])
                            
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in grade_scores if s.score is not None])
                            
                            if not class_df.empty and not grade_df.empty:
                                # 计算总分和排名
                                class_totals = class_df.groupby("student_id")["score"].sum().reset_index()
                                grade_totals = grade_df.groupby("student_id")["score"].sum().reset_index()
                                
                                class_totals["rank"] = class_totals["score"].rank(method="min", ascending=False).astype(int)
                                grade_totals["rank"] = grade_totals["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生排名
                                student_class_rank = class_totals[class_totals["student_id"] == student_id]
                                student_grade_rank = grade_totals[grade_totals["student_id"] == student_id]
                                
                                if not student_class_rank.empty and not student_grade_rank.empty:
                                    rank_history.append({
                                        "exam_id": exam.id,
                                        "exam_name": exam.name,
                                        "exam_date": exam.exam_date,
                                        "class_rank": int(student_class_rank["rank"].iloc[0]),
                                        "class_total": len(class_totals),
                                        "grade_rank": int(student_grade_rank["rank"].iloc[0]),
                                        "grade_total": len(grade_totals)
                                    })
        
        # 构建增强的响应数据
        enhanced_trend_data = {
            **trend_data,
            "grade_ranks": grade_ranks,
            "dual_rank": dual_rank,
            "rank_history": rank_history
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学生成绩趋势分析成功",
            data=enhanced_trend_data,
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
            f"获取学生成绩趋势分析失败: {str(e)}"
        )

# 班级对比分析
@router.get("/comparative", response_model=StandardResponse, summary="获取比较分析")
async def get_comparative_analysis(
    exam_id: int,
    target_type: str = Query(..., regex="^(class|grade)$"),
    target_ids: List[int] = Query(...),
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取比较分析
    
    - **exam_id**: 考试ID
    - **target_type**: 目标类型 (class:班级, grade:年级)
    - **target_ids**: 目标ID列表
    - **subject_id**: 学科ID (可选)
    
    权限要求：
    - 学生：无权进行比较分析
    - 教师：可以比较自己任教的班级
    - 班主任：可以比较自己管理的班级和同年级的其他班级
    - 管理员：可以比较任何班级或年级
    """
    try:
        # 验证考试
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到ID为{exam_id}的考试"
            )
            
        # 验证权限和目标存在
        target_names = []
        student_ids_by_target = {}
        
        if target_type == "class":
            for class_id in target_ids:
                await check_class_access(class_id, current_user)
                class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
                
                if not class_obj:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND,
                        f"未找到ID为{class_id}的班级"
                    )
                    
                # 获取班级学生
                students = await Student.filter(class_field_id=class_id)
                student_ids = [s.id for s in students]
                
                class_name = f"{class_obj.grade.name}{class_obj.name}" if hasattr(class_obj, "grade") else class_obj.name
                target_names.append(class_name)
                student_ids_by_target[class_id] = student_ids
        else:  # grade
            for grade_id in target_ids:
                if current_user.role not in ["admin", "headteacher"]:
                    return create_error_response(
                        status.HTTP_403_FORBIDDEN,
                        "您没有权限查看年级分析数据"
                    )
                    
                grade = await Grade.get_or_none(id=grade_id)
                if not grade:
                    return create_error_response(
                        status.HTTP_404_NOT_FOUND,
                        f"未找到ID为{grade_id}的年级"
                    )
                    
                # 获取年级下所有班级的学生
                classes = await Class.filter(grade_id=grade_id)
                class_ids = [c.id for c in classes]
                students = await Student.filter(class_field_id__in=class_ids)
                student_ids = [s.id for s in students]
                
                target_names.append(grade.name)
                student_ids_by_target[grade_id] = student_ids
                
        # 构建查询
        all_student_ids = []
        for ids in student_ids_by_target.values():
            all_student_ids.extend(ids)
            
        if not all_student_ids:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                "未找到任何学生数据"
            )
            
        # 查询条件
        query = Score.filter(student_id__in=all_student_ids, exam_id=exam_id)
        
        if subject_id:
            query = query.filter(subject_id=subject_id)
            subject = await Subject.get_or_none(id=subject_id)
            if not subject:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND,
                    f"未找到ID为{subject_id}的学科"
                )
            subject_name = subject.name
        else:
            # 获取所有学科
            subjects = await Subject.all()
            subject_name = "全部学科"
        
        # 获取成绩数据
        scores = await query.prefetch_related("student", "subject")
        
        # 使用pandas分析
        data = []
        for score in scores:
            data.append({
                "student_id": score.student_id,
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "score": score.score,
                "exam_id": score.exam_id,
                "target_id": score.student.class_field_id  # 班级分析使用班级ID
            })
            
        if not data:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                "未找到成绩数据"
            )
            
        df = pd.DataFrame(data)
        
        # 计算对比数据
        comparative_data = {
            "subject_name": subject_name,
            "comparison_type": target_type,
            "target_names": target_names,
            "average_scores": {},
            "pass_rates": {},
            "excellent_rates": {},
            "score_distributions": {}
        }
        
        for target_id, student_ids in student_ids_by_target.items():
            # 筛选当前目标的成绩
            if target_type == "class":
                target_scores = df[df["target_id"] == target_id]
            else:  # grade
                target_scores = df[df["student_id"].isin(student_ids)]
                
            if target_scores.empty:
                continue
                
            idx = target_ids.index(target_id)
            target_name = target_names[idx]
            
            # 计算平均分
            avg_score = round(target_scores["score"].mean(), 2)
            comparative_data["average_scores"][target_name] = avg_score
            
            # 计算及格率和优秀率
            total = len(target_scores)
            pass_count = len(target_scores[target_scores["score"] >= 60])
            excellent_count = len(target_scores[target_scores["score"] >= 90])
            
            pass_rate = round(pass_count * 100 / total, 2) if total > 0 else 0
            excellent_rate = round(excellent_count * 100 / total, 2) if total > 0 else 0
            
            comparative_data["pass_rates"][target_name] = pass_rate
            comparative_data["excellent_rates"][target_name] = excellent_rate
            
            # 计算分数段分布
            distribution = {
                "0-59": len(target_scores[target_scores["score"] < 60]),
                "60-69": len(target_scores[(target_scores["score"] >= 60) & (target_scores["score"] < 70)]),
                "70-79": len(target_scores[(target_scores["score"] >= 70) & (target_scores["score"] < 80)]),
                "80-89": len(target_scores[(target_scores["score"] >= 80) & (target_scores["score"] < 90)]),
                "90-100": len(target_scores[target_scores["score"] >= 90])
            }
            
            comparative_data["score_distributions"][target_name] = distribution
            
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取对比分析成功",
            data=comparative_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(e.status_code, e.detail)
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取对比分析失败: {str(e)}"
        )

# 导出分析报告
@router.post("/export", response_class=StreamingResponse, summary="导出分析报告")
async def export_analysis(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    导出分析报告
    
    - **report_type**: 报告类型
    - **target_ids**: 目标ID列表（学生/班级/年级ID）
    - **parameters**: 附加参数
    
    权限要求：
    - 学生：只能导出与自己相关的分析报告
    - 教师：可以导出自己任教班级和学科的分析报告
    - 班主任：可以导出自己管理班级的分析报告
    - 管理员：可以导出任何分析报告
    """
    try:
        # 根据报告类型处理
        if export_request.report_type == "student_trend":
            # 导出学生趋势分析
            student_id = export_request.data_id
            
            # 检查权限
            await check_student_access(student_id, current_user)
            
            # 获取学生信息和分析数据
            student = await Student.get_or_none(id=student_id).prefetch_related("class_field")
            if not student:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"未找到ID为{student_id}的学生"
                )
                
            # 获取成绩数据
            subject_id = export_request.parameters.get("subject_id") if export_request.parameters else None
            
            # 导出Excel报告
            if export_request.format == "excel":
                # 获取趋势分析数据
                trend_response = await get_student_trend(
                    student_id=student_id,
                    subject_id=subject_id,
                    limit=20,
                    current_user=current_user
                )
                
                if trend_response.code != status.HTTP_200_OK:
                    raise HTTPException(
                        status_code=trend_response.code,
                        detail=trend_response.message
                    )
                    
                trend_data = trend_response.data
                
                # 创建Excel
                output = io.BytesIO()
                excel_util = ExcelUtils()
                
                # 学生成绩趋势表
                excel_util.create_student_trend_excel(
                    output=output,
                    student_name=student.name,
                    student_code=student.student_code,
                    class_name=student.class_field.name if student.class_field else "",
                    trend_data=trend_data
                )
                
                # 设置文件名
                filename = f"{student.name}_成绩趋势分析_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                # 返回Excel
                output.seek(0)
                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"暂不支持{export_request.format}格式导出"
                )
        elif export_request.report_type == "comparative":
            # 处理对比分析导出
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="暂不支持此类型报告导出"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的报告类型: {export_request.report_type}"
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出分析报告失败: {str(e)}"
        )

# 后台处理分析任务的函数
async def process_analysis_task(task_id: int):
    """
    后台处理分析任务
    
    - **task_id**: 任务ID
    """
    try:
        # 获取任务
        task = await AnalysisTask.get_or_none(id=task_id)
        if not task:
            return
            
        # 更新任务状态
        task.status = "processing"
        task.progress = 10
        await task.save()
        
        # 获取任务参数
        parameters = task.parameters
        target_ids = parameters.get("target_ids", [])
        subject_ids = parameters.get("subject_ids")
        exam_ids = parameters.get("exam_ids")
        
        # 根据任务类型处理
        results = {}
        
        if task.task_type == "student_trend":
            # 学生成长轨迹分析
            student_id = target_ids[0] if target_ids else None
            
            if not student_id:
                task.status = "failed"
                task.results = {"error": "未提供学生ID"}
                await task.save()
                return
                
            # 获取学生信息
            student = await Student.get_or_none(id=student_id).prefetch_related("class_field")
            if not student:
                task.status = "failed"
                task.results = {"error": f"未找到ID为{student_id}的学生"}
                await task.save()
                return
                
            task.progress = 30
            await task.save()
            
            # 分析学生成绩趋势
            # ... 进行学生成绩趋势分析的代码 ...
            
            # 更新任务进度
            task.progress = 100
            task.status = "completed"
            task.completed_at = datetime.now()
            task.results = results
            await task.save()
        else:
            # 其他类型任务的处理逻辑
            # ...
            
            # 更新为失败状态
            task.status = "failed"
            task.results = {"error": f"不支持的任务类型: {task.task_type}"}
            await task.save()
    except Exception as e:
        # 更新为失败状态
        try:
            if task:
                task.status = "failed"
                task.results = {"error": str(e)}
                await task.save()
        except:
            pass 

# 班级成绩分析
@router.get("/class/{class_id}/scores", response_model=StandardResponse, summary="获取班级成绩统计分析")
async def analyze_class_scores(
    class_id: int,
    exam_id: int,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级成绩统计分析
    
    - **class_id**: 班级ID
    - **exam_id**: 考试ID
    - **subject_id**: 学科ID（可选，不提供则分析所有学科）
    """
    try:
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
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
        if subject_id:
            # 如果指定了学科，只查询该学科的成绩
            scores = await Score.filter(
                student_id__in=student_ids,
                exam_id=exam_id,
                subject_id=subject_id
            ).prefetch_related("student", "subject", "exam")
        else:
            # 如果没有指定学科，尝试使用exam_id字段查找同一考试的所有科目
            # 首先获取当前考试的exam_id
            if hasattr(exam, 'exam_id') and exam.exam_id:
                # 如果有exam_id，找出所有同一考试ID的考试记录
                exam_records = await Exam.filter(exam_id=exam.exam_id)
                exam_ids = [e.id for e in exam_records]
                # 查询这些考试的所有成绩
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id__in=exam_ids
                ).prefetch_related("student", "subject", "exam")
            else:
                # 如果没有exam_id，就只查当前考试的成绩
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id=exam_id
                ).prefetch_related("student", "subject", "exam")
        
        # 使用pandas进行数据分析
        if len(scores) > 0:
            # 创建DataFrame
            data = []
            for score in scores:
                data.append({
                    "student_id": score.student_id,
                    "student_name": score.student.name,
                    "student_code": score.student.student_code, 
                    "subject_id": score.subject_id,
                    "subject_name": score.subject.name,
                    "score": score.score,
                    "exam_id": score.exam_id
                })
            
            df = pd.DataFrame(data)
            
            # 计算统计数据
            total_students = len(students)
            scored_students = df["student_id"].nunique()
            completion_rate = round(scored_students * 100 / total_students, 2) if total_students > 0 else 0
            
            # 按学科分组计算统计数据
            subject_stats = {}
            if not df.empty:
                subject_groups = df.groupby("subject_name")
                
                for subject_name, group in subject_groups:
                    # 基本统计
                    avg_score = round(group["score"].mean(), 2)
                    max_score = group["score"].max()
                    min_score = group["score"].min()
                    count = len(group)
                    std_dev = round(group["score"].std(), 2) if len(group) > 1 else 0
                    median = group["score"].median()
                    
                    # 及格和优秀率
                    pass_count = len(group[group["score"] >= 60])
                    excellent_count = len(group[group["score"] >= 90])
                    good_count = len(group[(group["score"] >= 80) & (group["score"] < 90)])
                    pass_rate = round(pass_count * 100 / count, 2) if count > 0 else 0
                    excellent_rate = round(excellent_count * 100 / count, 2) if count > 0 else 0
                    good_rate = round(good_count * 100 / count, 2) if count > 0 else 0
                    
                    # 分数段分布
                    distribution = {
                        "0-59": len(group[group["score"] < 60]),
                        "60-69": len(group[(group["score"] >= 60) & (group["score"] < 70)]),
                        "70-79": len(group[(group["score"] >= 70) & (group["score"] < 80)]),
                        "80-89": len(group[(group["score"] >= 80) & (group["score"] < 90)]),
                        "90-100": len(group[group["score"] >= 90])
                    }
                    
                    # 计算分位数
                    percentiles = {
                        "25th": round(group["score"].quantile(0.25), 2),
                        "50th": round(group["score"].quantile(0.5), 2),
                        "75th": round(group["score"].quantile(0.75), 2),
                        "90th": round(group["score"].quantile(0.9), 2)
                    }
                    
                    subject_stats[subject_name] = {
                        "average_score": avg_score,
                        "median_score": median,
                        "max_score": max_score,
                        "min_score": min_score,
                        "standard_deviation": std_dev,
                        "count": count,
                        "pass_count": pass_count,
                        "excellent_count": excellent_count,
                        "good_count": good_count,
                        "pass_rate": pass_rate,
                        "excellent_rate": excellent_rate,
                        "good_rate": good_rate,
                        "score_distribution": distribution,
                        "percentiles": percentiles
                    }
            
            # 计算学生总分和排名 - 这里需要考虑多个学科的情况
            if subject_id:
                # 如果指定了学科，直接使用该学科的分数
                student_df = df.groupby("student_id").agg({
                    "student_name": "first",
                    "student_code": "first",
                    "score": "sum",  # 因为每个学生只有一条记录，所以sum等于该学科的分数
                    "subject_id": "count"  # 这里应该都是1
                }).reset_index()
                
                student_df.rename(columns={"subject_id": "subject_count"}, inplace=True)
                student_df["average_score"] = student_df["score"]  # 只有一个学科，平均分就是该学科分数
            else:
                # 如果是所有学科，需要按学生分组并计算总分和平均分
                student_df = df.groupby("student_id").agg({
                    "student_name": "first",
                    "student_code": "first",
                    "score": "sum",
                    "subject_id": "nunique"  # 使用nunique来获取学科数量
                }).reset_index()
                
                student_df.rename(columns={"subject_id": "subject_count"}, inplace=True)
                student_df["average_score"] = round(student_df["score"] / student_df["subject_count"], 2)
            
            # 计算学生排名
            student_df = student_df.sort_values("score", ascending=False)
            student_df["rank"] = student_df["score"].rank(method='min', ascending=False).astype(int)
            
            # 获取前10名学生
            top_students = []
            for _, row in student_df.head(10).iterrows():
                top_students.append({
                    "student_id": int(row["student_id"]),
                    "student_name": row["student_name"],
                    "student_code": row["student_code"],
                    "total_score": float(row["score"]),
                    "average_score": float(row["average_score"]),
                    "subject_count": int(row["subject_count"]),
                    "rank": int(row["rank"])
                })
            
            # 获取全班学生数据，带排名
            all_students = []
            for _, row in student_df.iterrows():
                all_students.append({
                    "student_id": int(row["student_id"]),
                    "student_name": row["student_name"],
                    "student_code": row["student_code"],
                    "total_score": float(row["score"]),
                    "average_score": float(row["average_score"]),
                    "subject_count": int(row["subject_count"]),
                    "rank": int(row["rank"])
                })
            
            # 计算班级总体统计
            if not df.empty and len(subject_stats) > 0:
                overall_stats = {
                    "average_score": round(df["score"].mean(), 2),
                    "median_score": round(df["score"].median(), 2),
                    "max_score": df["score"].max(),
                    "min_score": df["score"].min(),
                    "standard_deviation": round(df["score"].std(), 2) if len(df) > 1 else 0,
                    "total_scores": len(df),
                    "pass_rate": round(len(df[df["score"] >= 60]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "excellent_rate": round(len(df[df["score"] >= 90]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "good_rate": round(len(df[(df["score"] >= 80) & (df["score"] < 90)]) * 100 / len(df), 2) if len(df) > 0 else 0
                }
            else:
                overall_stats = {}
            
            # 如果有exam_id，则使用原始考试名称作为响应
            exam_name = exam.name
            if hasattr(exam, 'exam_id') and exam.exam_id:
                # 从exam_id中提取更简洁的考试名称
                parts = exam.exam_id.split('_')
                if len(parts) >= 3:  # 确保有足够的部分: 日期_年级_类型
                    date = parts[0]
                    exam_type = parts[2]  # 月考/期中/期末等
                    exam_name = f"{date} {exam_type}"
            
            # 班级名称
            grade_name = class_obj.grade.name if hasattr(class_obj, "grade") else ""
            class_full_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
            
            response_data = {
                "class_id": class_id,
                "class_name": class_obj.name,
                "class_full_name": class_full_name,
                "exam_id": exam_id,
                "exam_name": exam_name,
                "subject_count": len(subject_stats),
                "total_students": total_students,
                "scored_students": scored_students,
                "completion_rate": completion_rate,
                "subject_stats": subject_stats,
                "overall_stats": overall_stats,
                "top_students": top_students,
                "all_students": all_students
            }
        else:
            # 如果没有成绩数据
            grade_name = class_obj.grade.name if hasattr(class_obj, "grade") else ""
            class_full_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
            
            response_data = {
                "class_id": class_id,
                "class_name": class_obj.name,
                "class_full_name": class_full_name,
                "exam_id": exam_id,
                "exam_name": exam.name,
                "subject_count": 0,
                "total_students": len(students),
                "scored_students": 0,
                "completion_rate": 0,
                "subject_stats": {},
                "overall_stats": {},
                "top_students": [],
                "all_students": []
            }
        
        # 创建分析快照，用于历史记录
        snapshot_data = {
            "class_id": class_id,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "timestamp": datetime.now().isoformat(),
            "stats": response_data
        }
        
        # 异步创建快照
        await AnalysisSnapshot.create(
            snapshot_type="class_scores",
            target_id=class_id,
            target_type="class",
            data=snapshot_data,
            exam_id=exam_id,
            subject_id=subject_id
        )
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级成绩分析成功",
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
            f"获取班级成绩分析失败: {str(e)}"
        )

# 班级历史分析对比
@router.get("/class/{class_id}/historical", response_model=StandardResponse, summary="获取班级历史成绩对比分析")
async def get_class_historical_analysis(
    class_id: int,
    exam_ids: List[int] = Query(...),
    subject_id: Optional[int] = None,
    metric: str = Query("average_score", description="比较指标"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级多次考试的历史成绩对比分析
    
    - **class_id**: 班级ID
    - **exam_ids**: 考试ID列表（可指定多个考试进行对比）
    - **subject_id**: 学科ID（可选，不提供则分析所有学科）
    - **metric**: 比较指标，可选值: average_score, pass_rate, excellent_rate 等
    """
    try:
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查考试是否都存在
        exams = []
        for exam_id in exam_ids:
            exam = await Exam.get_or_none(id=exam_id)
            if not exam:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{exam_id}的考试"
                )
            exams.append(exam)
        
        # 获取班级学生
        students = await Student.filter(class_field_id=class_id)
        student_ids = [student.id for student in students]
        
        if not student_ids:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"该班级没有学生"
            )
        
        # 获取学科信息
        subject_name = "全部学科"
        if subject_id:
            subject = await Subject.get_or_none(id=subject_id)
            if not subject:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{subject_id}的学科"
                )
            subject_name = subject.name
        
        # 准备收集每次考试的分析数据
        historical_data = []
        
        # 对每个考试进行分析
        for exam in exams:
            # 构建查询
            if subject_id:
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id=exam.id,
                    subject_id=subject_id
                ).prefetch_related("student", "subject")
            else:
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id=exam.id
                ).prefetch_related("student", "subject")
            
            # 检查是否有数据
            if not scores:
                # 无数据时添加空的分析结果
                historical_data.append({
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "exam_date": exam.exam_date,
                    "metrics": {
                        "average_score": 0,
                        "pass_rate": 0,
                        "excellent_rate": 0,
                        "completion_rate": 0
                    },
                    "has_data": False
                })
                continue
            
            # 创建DataFrame进行分析
            data = []
            for score in scores:
                data.append({
                    "student_id": score.student_id,
                    "subject_id": score.subject_id,
                    "subject_name": score.subject.name,
                    "score": score.score
                })
            
            df = pd.DataFrame(data)
            
            # 计算指标
            total_students = len(students)
            scored_students = df["student_id"].nunique()
            completion_rate = round(scored_students * 100 / total_students, 2) if total_students > 0 else 0
            
            # 计算考试指标
            metrics = {}
            if not df.empty:
                metrics = {
                    "average_score": round(df["score"].mean(), 2),
                    "median_score": round(df["score"].median(), 2),
                    "pass_rate": round(len(df[df["score"] >= 60]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "excellent_rate": round(len(df[df["score"] >= 90]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "good_rate": round(len(df[(df["score"] >= 80) & (df["score"] < 90)]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "completion_rate": completion_rate
                }
            
            # 添加到历史数据
            historical_data.append({
                "exam_id": exam.id,
                "exam_name": exam.name,
                "exam_date": exam.exam_date,
                "metrics": metrics,
                "has_data": True
            })
        
        # 对历史数据按考试日期排序
        historical_data.sort(key=lambda x: x["exam_date"])
        
        # 提取用于可视化的数据序列
        series_data = {
            "exam_names": [item["exam_name"] for item in historical_data],
            "exam_dates": [item["exam_date"].strftime("%Y-%m-%d") if hasattr(item["exam_date"], "strftime") else item["exam_date"] for item in historical_data],
            "metrics": {}
        }
        
        # 准备各指标的数据
        metrics_list = ["average_score", "pass_rate", "excellent_rate", "completion_rate", "median_score", "good_rate"]
        for metric_name in metrics_list:
            series_data["metrics"][metric_name] = [
                item["metrics"].get(metric_name, 0) if item["has_data"] else None
                for item in historical_data
            ]
        
        # 班级名称
        grade_name = class_obj.grade.name if hasattr(class_obj, "grade") else ""
        class_full_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
        
        # 构建响应
        response_data = {
            "class_id": class_id,
            "class_name": class_obj.name,
            "class_full_name": class_full_name,
            "subject_name": subject_name,
            "exam_count": len(exams),
            "historical_data": historical_data,
            "series_data": series_data
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级历史成绩分析成功",
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
            f"获取班级历史成绩分析失败: {str(e)}"
        )

# 获取学生成绩统计分析
@router.get("/student/{student_id}/statistics", response_model=StandardResponse, summary="获取学生成绩统计分析")
async def get_student_score_statistics(
    student_id: int,
    exam_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取学生成绩统计分析
    
    - **student_id**: 学生ID
    - **exam_id**: 考试ID (可选，不提供则分析所有考试)
    """
    try:
        # 检查权限
        await check_student_access(student_id, current_user)
        
        # 获取学生信息
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
            
        # 获取成绩并预加载关联数据
        scores = await query.prefetch_related("subject", "exam")
        
        if not scores:
            # 无成绩数据
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到该学生的成绩数据"
            )
            
        # 创建DataFrame进行分析
        data = []
        for score in scores:
            data.append({
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "exam_id": score.exam_id,
                "exam_name": score.exam.name,
                "exam_date": score.exam.exam_date,
                "score": score.score,
                "ranking": score.ranking
            })
            
        df = pd.DataFrame(data)
        
        # 按学科统计
        subject_stats = {}
        if not df.empty:
            subject_groups = df.groupby("subject_name")
            
            for subject_name, group in subject_groups:
                # 基本统计
                avg_score = round(group["score"].mean(), 2)
                max_score = group["score"].max()
                min_score = group["score"].min()
                count = len(group)
                std_dev = round(group["score"].std(), 2) if len(group) > 1 else 0
                
                # 考试成绩趋势
                exam_scores = []
                for _, row in group.sort_values("exam_date").iterrows():
                    exam_scores.append({
                        "exam_id": row["exam_id"],
                        "exam_name": row["exam_name"],
                        "exam_date": row["exam_date"],
                        "score": row["score"],
                        "ranking": row["ranking"] if pd.notna(row["ranking"]) else None
                    })
                
                # 计算进步情况
                progress = None
                if len(exam_scores) >= 2:
                    first_score = exam_scores[0]["score"]
                    last_score = exam_scores[-1]["score"]
                    progress = {
                        "first_score": first_score,
                        "last_score": last_score,
                        "change": round(last_score - first_score, 2),
                        "percent_change": round((last_score - first_score) * 100 / first_score, 2) if first_score > 0 else None
                    }
                
                subject_stats[subject_name] = {
                    "average_score": avg_score,
                    "max_score": max_score,
                    "min_score": min_score,
                    "standard_deviation": std_dev,
                    "exam_count": count,
                    "exam_scores": exam_scores,
                    "progress": progress
                }
        
        # 总体成绩统计
        overall_stats = {
            "average_score": round(df["score"].mean(), 2),
            "max_score": df["score"].max(),
            "min_score": df["score"].min(),
            "standard_deviation": round(df["score"].std(), 2) if len(df) > 1 else 0,
            "total_exams": df["exam_id"].nunique(),
            "total_subjects": df["subject_id"].nunique(),
            "total_scores": len(df)
        }
        
        # 获取班级信息
        class_name = student.class_field.name if student.class_field else ""
        grade_name = ""
        if student.class_field and hasattr(student.class_field, "grade"):
            grade_name = student.class_field.grade.name
            
        class_full_name = f"{grade_name}{class_name}" if grade_name else class_name
        
        # 构建响应
        response_data = {
            "student_id": student.id,
            "student_name": student.name,
            "student_code": student.student_code,
            "class_id": student.class_field_id,
            "class_name": class_name,
            "class_full_name": class_full_name,
            "overall_stats": overall_stats,
            "subject_stats": subject_stats
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取学生成绩统计分析成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(e.status_code, e.detail)
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取学生成绩统计分析失败: {str(e)}"
        )

# 获取增强版学生趋势分析（包含排名信息）
@router.get("/student/{student_id}/enhanced_trend", response_model=StandardResponse, summary="获取增强版学生成绩趋势分析")
async def get_enhanced_student_trend(
    student_id: int,
    subject_id: Optional[int] = None,
    limit: int = Query(10, description="最大记录数"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取增强版学生成绩趋势分析，包含年级排名和历史轨迹
    
    - **student_id**: 学生ID
    - **subject_id**: 学科ID (可选)
    - **limit**: 最大记录数（默认10）
    """
    try:
        # 检查权限
        await check_student_access(student_id, current_user)
        
        # 获取学生信息
        student = await Student.get_or_none(id=student_id).prefetch_related("class_field", "class_field__grade")
        if not student:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到ID为{student_id}的学生"
            )
            
        # 获取班级信息和年级信息
        class_id = student.class_field_id
        grade_id = None
        if student.class_field and hasattr(student.class_field, "grade_id"):
            grade_id = student.class_field.grade_id
            
        # 构建查询
        query = Score.filter(student_id=student_id)
        if subject_id:
            query = query.filter(subject_id=subject_id)
            
        # 获取成绩并预加载关联数据
        scores = await query.prefetch_related("subject", "exam").order_by("-exam__exam_date").limit(limit)
        
        if not scores:
            return create_error_response(
                status.HTTP_404_NOT_FOUND,
                f"未找到该学生的成绩数据"
            )
            
        # 收集考试ID以获取排名历史
        exam_ids = [score.exam_id for score in scores]
        unique_exam_ids = list(set(exam_ids))
        
        # 创建DataFrame进行分析
        data = []
        for score in scores:
            data.append({
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "exam_id": score.exam_id,
                "exam_name": score.exam.name,
                "exam_date": score.exam.exam_date,
                "score": score.score,
                "ranking": score.ranking
            })
            
        df = pd.DataFrame(data)
        
        # 计算趋势数据
        trend_data = {
            "exam_labels": [],
            "series_data": {},
            "radar_data": {
                "indicators": [],
                "series_data": []
            }
        }
        
        # 处理每个学科的趋势
        subject_scores = {}
        
        if not df.empty:
            # 按学科和考试排序
            df_sorted = df.sort_values(["subject_name", "exam_date"])
            
            # 收集每个学科的所有成绩记录
            for subject_name, group in df_sorted.groupby("subject_name"):
                scores_list = []
                for _, row in group.iterrows():
                    scores_list.append({
                        "exam_id": row["exam_id"],
                        "exam_name": row["exam_name"],
                        "exam_date": row["exam_date"],
                        "score": row["score"],
                        "ranking": row["ranking"] if pd.notna(row["ranking"]) else None
                    })
                subject_scores[subject_name] = scores_list
                
                # 为每个考试添加数据点
                if subject_name not in trend_data["series_data"]:
                    trend_data["series_data"][subject_name] = []
                    
                for _, row in group.iterrows():
                    exam_name = row["exam_name"]
                    if exam_name not in trend_data["exam_labels"]:
                        trend_data["exam_labels"].append(exam_name)
                    trend_data["series_data"][subject_name].append(float(row["score"]))
                    
                # 添加雷达图指标
                if len(scores_list) > 0:
                    latest_score = scores_list[-1]["score"]
                    trend_data["radar_data"]["indicators"].append({
                        "name": subject_name,
                        "max": 100
                    })
                    trend_data["radar_data"]["series_data"].append(float(latest_score))
        
        # 新增：获取年级排名数据
        grade_ranks = {}
        dual_rank = None
        rank_history = []
        
        # 预先获取所需的数据，减少重复查询
        if grade_id:
            # 1. 一次性获取年级内所有班级
            grade_classes = await Class.filter(grade_id=grade_id)
            grade_class_ids = [c.id for c in grade_classes]
            
            # 2. 一次性获取年级内所有学生
            grade_students = await Student.filter(class_field_id__in=grade_class_ids)
            grade_student_ids = [s.id for s in grade_students]
            
            # 3. 一次性获取班级内所有学生
            class_students = await Student.filter(class_field_id=class_id)
            class_student_ids = [s.id for s in class_students]
            
            # 4. 如果数据不为空，继续处理排名数据
            if not df.empty and len(grade_student_ids) > 0:
                # 获取所有需要查询的科目和考试组合
                subject_exam_pairs = []
                for subject_name, subject_group in df_sorted.groupby("subject_name"):
                    if len(subject_group) > 0:
                        # 获取最新考试记录
                        latest_exam = subject_group.iloc[-1]
                        subject_exam_pairs.append((latest_exam["subject_id"], latest_exam["exam_id"]))
                
                # 批量获取所有需要的成绩数据
                all_subject_scores = {}
                if subject_exam_pairs:
                    for subject_id, exam_id in subject_exam_pairs:
                        # 查询该考试该学科的所有成绩
                        grade_scores = await Score.filter(
                            exam_id=exam_id,
                            subject_id=subject_id,
                            student_id__in=grade_student_ids
                        )
                        all_subject_scores[(subject_id, exam_id)] = grade_scores
                
                # 处理单科年级排名
                for subject_name, subject_group in df_sorted.groupby("subject_name"):
                    if len(subject_group) > 0:
                        latest_exam = subject_group.iloc[-1]
                        subject_id = latest_exam["subject_id"]
                        exam_id = latest_exam["exam_id"]
                        
                        grade_scores = all_subject_scores.get((subject_id, exam_id), [])
                        
                        if grade_scores:
                            # 创建DataFrame计算排名
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "score": s.score
                            } for s in grade_scores if s.score is not None])
                            
                            if not grade_df.empty:
                                # 对有效成绩进行排名（使用min方法确保并列排名）
                                grade_df["rank"] = grade_df["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生在年级中的排名
                                student_rank = grade_df[grade_df["student_id"] == student_id]
                                
                                if not student_rank.empty:
                                    rank = int(student_rank["rank"].iloc[0])
                                    total = len(grade_df)
                                    percentage = round(rank * 100 / total, 2)
                                    percentile = round(100 - percentage, 2)
                                    
                                    grade_ranks[subject_name] = {
                                        "absolute_rank": rank,
                                        "total_students": total,
                                        "percentage": percentage,
                                        "percentile": percentile
                                    }
            
                # 获取双维度排名数据
                if unique_exam_ids:
                    # 获取最近的一次考试
                    recent_exams = await Exam.filter(id__in=unique_exam_ids).order_by("-exam_date")
                    if recent_exams:
                        recent_exam = recent_exams[0]
                        
                        # 批量获取成绩数据
                        all_class_scores = await Score.filter(
                            exam_id=recent_exam.id,
                            student_id__in=class_student_ids
                        )
                        
                        all_grade_scores = await Score.filter(
                            exam_id=recent_exam.id,
                            student_id__in=grade_student_ids
                        )
                        
                        if all_class_scores and all_grade_scores:
                            # 创建DataFrame计算班级排名
                            class_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in all_class_scores if s.score is not None])
                            
                            # 创建DataFrame计算年级排名
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in all_grade_scores if s.score is not None])
                            
                            if not class_df.empty and not grade_df.empty:
                                # 计算每个学生的总分
                                class_totals = class_df.groupby("student_id")["score"].sum().reset_index()
                                grade_totals = grade_df.groupby("student_id")["score"].sum().reset_index()
                                
                                # 计算排名（使用min方法确保并列排名）
                                class_totals["rank"] = class_totals["score"].rank(method="min", ascending=False).astype(int)
                                grade_totals["rank"] = grade_totals["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生排名
                                student_class_rank = class_totals[class_totals["student_id"] == student_id]
                                student_grade_rank = grade_totals[grade_totals["student_id"] == student_id]
                                
                                if not student_class_rank.empty and not student_grade_rank.empty:
                                    class_rank = int(student_class_rank["rank"].iloc[0])
                                    class_total = len(class_totals)
                                    class_percentile = round(100 - (class_rank * 100 / class_total), 2)
                                    
                                    grade_rank = int(student_grade_rank["rank"].iloc[0])
                                    grade_total = len(grade_totals)
                                    grade_percentile = round(100 - (grade_rank * 100 / grade_total), 2)
                                    
                                    dual_rank = {
                                        "class_rank": class_rank,
                                        "class_total": class_total,
                                        "grade_rank": grade_rank,
                                        "grade_total": grade_total,
                                        "class_percentile": class_percentile,
                                        "grade_percentile": grade_percentile
                                    }
                
                # 获取排名历史
                if unique_exam_ids and len(class_student_ids) > 0 and len(grade_student_ids) > 0:
                    # 批量获取所有相关考试的数据
                    all_exams = await Exam.filter(id__in=unique_exam_ids).order_by("-exam_date")
                    
                    # 批量获取所有考试的班级和年级成绩
                    batch_class_scores = {}
                    batch_grade_scores = {}
                    
                    for exam in all_exams:
                        # 批量获取该考试的班级和年级成绩
                        class_scores = await Score.filter(
                            exam_id=exam.id,
                            student_id__in=class_student_ids
                        )
                        
                        grade_scores = await Score.filter(
                            exam_id=exam.id,
                            student_id__in=grade_student_ids
                        )
                        
                        batch_class_scores[exam.id] = class_scores
                        batch_grade_scores[exam.id] = grade_scores
                    
                    # 处理每个考试的排名数据
                    for exam in all_exams:
                        class_scores = batch_class_scores.get(exam.id, [])
                        grade_scores = batch_grade_scores.get(exam.id, [])
                        
                        if class_scores and grade_scores:
                            # 创建DataFrame
                            class_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in class_scores if s.score is not None])
                            
                            grade_df = pd.DataFrame([{
                                "student_id": s.student_id,
                                "subject_id": s.subject_id,
                                "score": s.score
                            } for s in grade_scores if s.score is not None])
                            
                            if not class_df.empty and not grade_df.empty:
                                # 计算总分和排名
                                class_totals = class_df.groupby("student_id")["score"].sum().reset_index()
                                grade_totals = grade_df.groupby("student_id")["score"].sum().reset_index()
                                
                                class_totals["rank"] = class_totals["score"].rank(method="min", ascending=False).astype(int)
                                grade_totals["rank"] = grade_totals["score"].rank(method="min", ascending=False).astype(int)
                                
                                # 获取学生排名
                                student_class_rank = class_totals[class_totals["student_id"] == student_id]
                                student_grade_rank = grade_totals[grade_totals["student_id"] == student_id]
                                
                                if not student_class_rank.empty and not student_grade_rank.empty:
                                    rank_history.append({
                                        "exam_id": exam.id,
                                        "exam_name": exam.name,
                                        "exam_date": exam.exam_date,
                                        "class_rank": int(student_class_rank["rank"].iloc[0]),
                                        "class_total": len(class_totals),
                                        "grade_rank": int(student_grade_rank["rank"].iloc[0]),
                                        "grade_total": len(grade_totals)
                                    })
        
        # 构建增强的响应数据
        enhanced_trend_data = {
            **trend_data,
            "grade_ranks": grade_ranks,
            "dual_rank": dual_rank,
            "rank_history": rank_history
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取增强版学生成绩趋势分析成功",
            data=enhanced_trend_data,
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
            f"获取增强版学生成绩趋势分析失败: {str(e)}"
        ) 

# 班级成绩段位分布对比
@router.get("/class/level_distribution", response_model=StandardResponse, summary="获取班级段位分布对比分析")
async def analyze_class_level_distribution(
    class_ids: List[int] = Query(..., description="班级ID列表"),
    exam_id: int = Query(..., description="考试ID"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取多个班级的成绩段位分布对比分析
    
    - **class_ids**: 班级ID列表（可指定多个班级进行对比）
    - **exam_id**: 考试ID
    """
    try:
        # 检查用户是否有权限访问所有班级数据
        for class_id in class_ids:
            await check_class_access(class_id, current_user)
        
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{exam_id}的考试"
            )
        
        # 获取前一次考试，用于计算进步指数
        previous_exam = await Exam.filter(exam_date__lt=exam.exam_date).order_by("-exam_date").first()
        
        # 查询班级信息
        classes = []
        for class_id in class_ids:
            class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
            if not class_obj:
                return create_error_response(
                    status.HTTP_404_NOT_FOUND, 
                    f"未找到ID为{class_id}的班级"
                )
            classes.append(class_obj)
        
        # 确定所有班级是否在同一年级
        grade_ids = set([c.grade_id for c in classes if hasattr(c, 'grade_id')])
        
        if len(grade_ids) != 1:
            return create_error_response(
                status.HTTP_400_BAD_REQUEST, 
                "所选班级不在同一年级，无法进行对比分析"
            )
        
        grade_id = list(grade_ids)[0]
        
        # 获取年级内所有班级（用于计算年级基准线）
        grade_classes = await Class.filter(grade_id=grade_id)
        all_grade_class_ids = [c.id for c in grade_classes]
        
        # 保存每个班级的段位分布结果
        class_distributions = []
        
        # 计算各班级段位分布
        for class_obj in classes:
            # 获取班级学生
            students = await Student.filter(class_field_id=class_obj.id)
            student_ids = [student.id for student in students]
            
            if not student_ids:
                continue
            
            # 获取当前考试的成绩
            scores = await Score.filter(
                student_id__in=student_ids,
                exam_id=exam_id
            ).prefetch_related("student", "subject")
            
            if not scores:
                continue
            
            # 创建DataFrame
            data = []
            for score in scores:
                data.append({
                    "student_id": score.student_id,
                    "subject_id": score.subject_id,
                    "score": score.score
                })
            
            df = pd.DataFrame(data)
            
            if df.empty:
                continue
            
            # 计算每个学生的总分和平均分
            student_totals = df.groupby("student_id").agg({
                "score": "sum",
                "subject_id": "count"
            }).reset_index()
            
            student_totals.rename(columns={"subject_id": "subject_count"}, inplace=True)
            
            # 计算每个学生的平均分（百分比）
            student_totals["average_percent"] = (student_totals["score"] / 
                                               (student_totals["subject_count"] * 100)) * 100
            
            # 根据段位标准划分
            excellent_count = len(student_totals[student_totals["average_percent"] >= 80])
            good_count = len(student_totals[(student_totals["average_percent"] >= 70) & 
                                          (student_totals["average_percent"] < 80)])
            pass_count = len(student_totals[(student_totals["average_percent"] >= 60) & 
                                          (student_totals["average_percent"] < 70)])
            fail_count = len(student_totals[student_totals["average_percent"] < 60])
            
            total_count = len(student_totals)
            
            # 计算各段位占比
            excellent_percentage = round(excellent_count * 100 / total_count, 2) if total_count > 0 else 0
            good_percentage = round(good_count * 100 / total_count, 2) if total_count > 0 else 0
            pass_percentage = round(pass_count * 100 / total_count, 2) if total_count > 0 else 0
            fail_percentage = round(fail_count * 100 / total_count, 2) if total_count > 0 else 0
            
            # 保存该班级的段位分布
            distributions = [
                {
                    "level": "excellent",
                    "count": excellent_count,
                    "percentage": excellent_percentage
                },
                {
                    "level": "good",
                    "count": good_count,
                    "percentage": good_percentage
                },
                {
                    "level": "pass",
                    "count": pass_count,
                    "percentage": pass_percentage
                },
                {
                    "level": "fail",
                    "count": fail_count,
                    "percentage": fail_percentage
                }
            ]
            
            class_distributions.append({
                "class_id": class_obj.id,
                "class_name": class_obj.name,
                "distributions": distributions
            })
        
        # 计算年级基准线
        # 获取年级所有学生
        grade_students = await Student.filter(class_field_id__in=all_grade_class_ids)
        grade_student_ids = [student.id for student in grade_students]
        
        # 获取年级所有成绩
        grade_scores = await Score.filter(
            student_id__in=grade_student_ids,
            exam_id=exam_id
        )
        
        # 计算年级段位分布
        grade_benchmarks = []
        
        if grade_scores:
            # 创建DataFrame
            grade_data = []
            for score in grade_scores:
                grade_data.append({
                    "student_id": score.student_id,
                    "subject_id": score.subject_id,
                    "score": score.score
                })
            
            grade_df = pd.DataFrame(grade_data)
            
            if not grade_df.empty:
                # 计算每个学生的总分和平均分
                grade_totals = grade_df.groupby("student_id").agg({
                    "score": "sum",
                    "subject_id": "count"
                }).reset_index()
                
                grade_totals.rename(columns={"subject_id": "subject_count"}, inplace=True)
                
                # 计算每个学生的平均分（百分比）
                grade_totals["average_percent"] = (grade_totals["score"] / 
                                                 (grade_totals["subject_count"] * 100)) * 100
                
                # 根据段位标准划分
                grade_excellent_count = len(grade_totals[grade_totals["average_percent"] >= 80])
                grade_good_count = len(grade_totals[(grade_totals["average_percent"] >= 70) & 
                                                  (grade_totals["average_percent"] < 80)])
                grade_pass_count = len(grade_totals[(grade_totals["average_percent"] >= 60) & 
                                                  (grade_totals["average_percent"] < 70)])
                grade_fail_count = len(grade_totals[grade_totals["average_percent"] < 60])
                
                grade_total_count = len(grade_totals)
                
                # 计算各段位占比
                grade_excellent_percentage = round(grade_excellent_count * 100 / grade_total_count, 2) if grade_total_count > 0 else 0
                grade_good_percentage = round(grade_good_count * 100 / grade_total_count, 2) if grade_total_count > 0 else 0
                grade_pass_percentage = round(grade_pass_count * 100 / grade_total_count, 2) if grade_total_count > 0 else 0
                grade_fail_percentage = round(grade_fail_count * 100 / grade_total_count, 2) if grade_total_count > 0 else 0
                
                # 设置年级基准线
                grade_benchmarks = [
                    {
                        "level": "excellent",
                        "average_percentage": grade_excellent_percentage
                    },
                    {
                        "level": "good",
                        "average_percentage": grade_good_percentage
                    },
                    {
                        "level": "pass",
                        "average_percentage": grade_pass_percentage
                    },
                    {
                        "level": "fail",
                        "average_percentage": grade_fail_percentage
                    }
                ]
        
        # 计算班级进步指数（如果有前一次考试）
        class_progress = []
        
        if previous_exam:
            # 获取前一次考试的段位分布
            previous_distributions = {}
            
            for class_obj in classes:
                # 获取班级学生
                students = await Student.filter(class_field_id=class_obj.id)
                student_ids = [student.id for student in students]
                
                if not student_ids:
                    continue
                
                # 获取前一次考试的成绩
                previous_scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id=previous_exam.id
                )
                
                if not previous_scores:
                    continue
                
                # 创建DataFrame
                data = []
                for score in previous_scores:
                    data.append({
                        "student_id": score.student_id,
                        "subject_id": score.subject_id,
                        "score": score.score
                    })
                
                previous_df = pd.DataFrame(data)
                
                if previous_df.empty:
                    continue
                
                # 计算每个学生的总分和平均分
                previous_totals = previous_df.groupby("student_id").agg({
                    "score": "sum",
                    "subject_id": "count"
                }).reset_index()
                
                previous_totals.rename(columns={"subject_id": "subject_count"}, inplace=True)
                
                # 计算每个学生的平均分（百分比）
                previous_totals["average_percent"] = (previous_totals["score"] / 
                                                   (previous_totals["subject_count"] * 100)) * 100
                
                # 根据段位标准划分
                prev_excellent_count = len(previous_totals[previous_totals["average_percent"] >= 80])
                prev_good_count = len(previous_totals[(previous_totals["average_percent"] >= 70) & 
                                                    (previous_totals["average_percent"] < 80)])
                prev_pass_count = len(previous_totals[(previous_totals["average_percent"] >= 60) & 
                                                    (previous_totals["average_percent"] < 70)])
                prev_fail_count = len(previous_totals[previous_totals["average_percent"] < 60])
                
                previous_distributions[class_obj.id] = {
                    "excellent": prev_excellent_count,
                    "good": prev_good_count,
                    "pass": prev_pass_count,
                    "fail": prev_fail_count,
                    "total": len(previous_totals)
                }
            
            # 计算每个班级的进步指数
            for class_dist in class_distributions:
                class_id = class_dist["class_id"]
                
                # 如果没有前一次考试的数据，跳过
                if class_id not in previous_distributions:
                    continue
                
                # 获取当前分布和前一次分布
                current_dist = {d["level"]: d["count"] for d in class_dist["distributions"]}
                prev_dist = previous_distributions[class_id]
                
                # 计算段位变化率
                level_changes = {}
                
                # 优秀率变化
                excellent_change = current_dist.get("excellent", 0) - prev_dist.get("excellent", 0)
                excellent_change_rate = round(excellent_change * 100 / prev_dist.get("excellent", 1), 2) \
                    if prev_dist.get("excellent", 0) > 0 else (100 if excellent_change > 0 else 0)
                level_changes["excellent"] = excellent_change_rate
                
                # 良好率变化
                good_change = current_dist.get("good", 0) - prev_dist.get("good", 0)
                good_change_rate = round(good_change * 100 / prev_dist.get("good", 1), 2) \
                    if prev_dist.get("good", 0) > 0 else (100 if good_change > 0 else 0)
                level_changes["good"] = good_change_rate
                
                # 及格率变化
                pass_change = current_dist.get("pass", 0) - prev_dist.get("pass", 0)
                pass_change_rate = round(pass_change * 100 / prev_dist.get("pass", 1), 2) \
                    if prev_dist.get("pass", 0) > 0 else (100 if pass_change > 0 else 0)
                level_changes["pass"] = pass_change_rate
                
                # 不及格率变化（降低为正向）
                fail_change = prev_dist.get("fail", 0) - current_dist.get("fail", 0)
                fail_change_rate = round(fail_change * 100 / prev_dist.get("fail", 1), 2) \
                    if prev_dist.get("fail", 0) > 0 else (100 if fail_change > 0 else 0)
                level_changes["fail"] = fail_change_rate
                
                # 计算综合进步指数（加权平均）
                progress_index = round(
                    excellent_change_rate * 0.4 +
                    good_change_rate * 0.3 +
                    pass_change_rate * 0.2 +
                    fail_change_rate * 0.1,
                    2
                )
                
                class_progress.append({
                    "class_id": class_id,
                    "class_name": class_dist["class_name"],
                    "progress_index": progress_index,
                    "level_changes": level_changes,
                    "rank": 0  # 暂时设为0，下面会重新计算
                })
            
            # 计算进步指数排名
            if class_progress:
                # 按进步指数降序排序
                class_progress.sort(key=lambda x: x["progress_index"], reverse=True)
                
                # 分配排名
                for i, progress in enumerate(class_progress):
                    progress["rank"] = i + 1
        
        # 构建响应数据
        response_data = {
            "exam_id": exam_id,
            "exam_name": exam.name,
            "exam_date": exam.exam_date,
            "grade_id": grade_id,
            "class_distributions": class_distributions,
            "grade_benchmarks": grade_benchmarks,
            "class_progress": class_progress
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级段位分布对比分析成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(e.status_code, e.detail)
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取班级段位分布对比分析失败: {str(e)}"
        )

@router.get("/class/{class_id}/benchmark", response_model=StandardResponse, summary="获取班级成绩统计分析")
async def get_class_benchmark(
    class_id: int,
    exam_id: int,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级成绩统计分析
    
    - **class_id**: 班级ID
    - **exam_id**: 考试ID
    - **subject_id**: 学科ID (可选)
    
    权限要求：
    - 学生：可以查看自己所在班级的统计分析，需要班主任授权
    - 教师：可以查看自己任教班级的统计分析
    - 班主任：可以查看自己管理班级的统计分析
    - 管理员：可以查看任何班级的统计分析
    """
    try:
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
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
        if subject_id:
            # 如果指定了学科，只查询该学科的成绩
            scores = await Score.filter(
                student_id__in=student_ids,
                exam_id=exam_id,
                subject_id=subject_id
            ).prefetch_related("student", "subject", "exam")
        else:
            # 如果没有指定学科，尝试使用exam_id字段查找同一考试的所有科目
            # 首先获取当前考试的exam_id
            if hasattr(exam, 'exam_id') and exam.exam_id:
                # 如果有exam_id，找出所有同一考试ID的考试记录
                exam_records = await Exam.filter(exam_id=exam.exam_id)
                exam_ids = [e.id for e in exam_records]
                # 查询这些考试的所有成绩
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id__in=exam_ids
                ).prefetch_related("student", "subject", "exam")
            else:
                # 如果没有exam_id，就只查当前考试的成绩
                scores = await Score.filter(
                    student_id__in=student_ids,
                    exam_id=exam_id
                ).prefetch_related("student", "subject", "exam")
        
        # 使用pandas进行数据分析
        if len(scores) > 0:
            # 创建DataFrame
            data = []
            for score in scores:
                data.append({
                    "student_id": score.student_id,
                    "student_name": score.student.name,
                    "student_code": score.student.student_code, 
                    "subject_id": score.subject_id,
                    "subject_name": score.subject.name,
                    "score": score.score,
                    "exam_id": score.exam_id
                })
            
            df = pd.DataFrame(data)
            
            # 计算统计数据
            total_students = len(students)
            scored_students = df["student_id"].nunique()
            completion_rate = round(scored_students * 100 / total_students, 2) if total_students > 0 else 0
            
            # 按学科分组计算统计数据
            subject_stats = {}
            if not df.empty:
                subject_groups = df.groupby("subject_name")
                
                for subject_name, group in subject_groups:
                    # 基本统计
                    avg_score = round(group["score"].mean(), 2)
                    max_score = group["score"].max()
                    min_score = group["score"].min()
                    count = len(group)
                    std_dev = round(group["score"].std(), 2) if len(group) > 1 else 0
                    median = group["score"].median()
                    
                    # 及格和优秀率
                    pass_count = len(group[group["score"] >= 60])
                    excellent_count = len(group[group["score"] >= 90])
                    good_count = len(group[(group["score"] >= 80) & (group["score"] < 90)])
                    pass_rate = round(pass_count * 100 / count, 2) if count > 0 else 0
                    excellent_rate = round(excellent_count * 100 / count, 2) if count > 0 else 0
                    good_rate = round(good_count * 100 / count, 2) if count > 0 else 0
                    
                    # 分数段分布
                    distribution = {
                        "0-59": len(group[group["score"] < 60]),
                        "60-69": len(group[(group["score"] >= 60) & (group["score"] < 70)]),
                        "70-79": len(group[(group["score"] >= 70) & (group["score"] < 80)]),
                        "80-89": len(group[(group["score"] >= 80) & (group["score"] < 90)]),
                        "90-100": len(group[group["score"] >= 90])
                    }
                    
                    # 计算分位数
                    percentiles = {
                        "25th": round(group["score"].quantile(0.25), 2),
                        "50th": round(group["score"].quantile(0.5), 2),
                        "75th": round(group["score"].quantile(0.75), 2),
                        "90th": round(group["score"].quantile(0.9), 2)
                    }
                    
                    subject_stats[subject_name] = {
                        "average_score": avg_score,
                        "median_score": median,
                        "max_score": max_score,
                        "min_score": min_score,
                        "standard_deviation": std_dev,
                        "count": count,
                        "pass_count": pass_count,
                        "excellent_count": excellent_count,
                        "good_count": good_count,
                        "pass_rate": pass_rate,
                        "excellent_rate": excellent_rate,
                        "good_rate": good_rate,
                        "score_distribution": distribution,
                        "percentiles": percentiles
                    }
            
            # 计算学生总分和排名 - 这里需要考虑多个学科的情况
            if subject_id:
                # 如果指定了学科，直接使用该学科的分数
                student_df = df.groupby("student_id").agg({
                    "student_name": "first",
                    "student_code": "first",
                    "score": "sum",  # 因为每个学生只有一条记录，所以sum等于该学科的分数
                    "subject_id": "count"  # 这里应该都是1
                }).reset_index()
                
                student_df.rename(columns={"subject_id": "subject_count"}, inplace=True)
                student_df["average_score"] = student_df["score"]  # 只有一个学科，平均分就是该学科分数
            else:
                # 如果是所有学科，需要按学生分组并计算总分和平均分
                student_df = df.groupby("student_id").agg({
                    "student_name": "first",
                    "student_code": "first",
                    "score": "sum",
                    "subject_id": "nunique"  # 使用nunique来获取学科数量
                }).reset_index()
                
                student_df.rename(columns={"subject_id": "subject_count"}, inplace=True)
                student_df["average_score"] = round(student_df["score"] / student_df["subject_count"], 2)
            
            # 计算学生排名
            student_df = student_df.sort_values("score", ascending=False)
            student_df["rank"] = student_df["score"].rank(method='min', ascending=False).astype(int)
            
            # 获取前10名学生
            top_students = []
            for _, row in student_df.head(10).iterrows():
                top_students.append({
                    "student_id": int(row["student_id"]),
                    "student_name": row["student_name"],
                    "student_code": row["student_code"],
                    "total_score": float(row["score"]),
                    "average_score": float(row["average_score"]),
                    "subject_count": int(row["subject_count"]),
                    "rank": int(row["rank"])
                })
            
            # 获取全班学生数据，带排名
            all_students = []
            for _, row in student_df.iterrows():
                all_students.append({
                    "student_id": int(row["student_id"]),
                    "student_name": row["student_name"],
                    "student_code": row["student_code"],
                    "total_score": float(row["score"]),
                    "average_score": float(row["average_score"]),
                    "subject_count": int(row["subject_count"]),
                    "rank": int(row["rank"])
                })
            
            # 计算班级总体统计
            if not df.empty and len(subject_stats) > 0:
                overall_stats = {
                    "average_score": round(df["score"].mean(), 2),
                    "median_score": round(df["score"].median(), 2),
                    "max_score": df["score"].max(),
                    "min_score": df["score"].min(),
                    "standard_deviation": round(df["score"].std(), 2) if len(df) > 1 else 0,
                    "total_scores": len(df),
                    "pass_rate": round(len(df[df["score"] >= 60]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "excellent_rate": round(len(df[df["score"] >= 90]) * 100 / len(df), 2) if len(df) > 0 else 0,
                    "good_rate": round(len(df[(df["score"] >= 80) & (df["score"] < 90)]) * 100 / len(df), 2) if len(df) > 0 else 0
                }
            else:
                overall_stats = {}
            
            # 如果有exam_id，则使用原始考试名称作为响应
            exam_name = exam.name
            if hasattr(exam, 'exam_id') and exam.exam_id:
                # 从exam_id中提取更简洁的考试名称
                parts = exam.exam_id.split('_')
                if len(parts) >= 3:  # 确保有足够的部分: 日期_年级_类型
                    date = parts[0]
                    exam_type = parts[2]  # 月考/期中/期末等
                    exam_name = f"{date} {exam_type}"
            
            # 班级名称
            grade_name = class_obj.grade.name if hasattr(class_obj, "grade") else ""
            class_full_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
            
            response_data = {
                "class_id": class_id,
                "class_name": class_obj.name,
                "class_full_name": class_full_name,
                "exam_id": exam_id,
                "exam_name": exam_name,
                "subject_count": len(subject_stats),
                "total_students": total_students,
                "scored_students": scored_students,
                "completion_rate": completion_rate,
                "subject_stats": subject_stats,
                "overall_stats": overall_stats,
                "top_students": top_students,
                "all_students": all_students
            }
        else:
            # 如果没有成绩数据
            grade_name = class_obj.grade.name if hasattr(class_obj, "grade") else ""
            class_full_name = f"{grade_name}{class_obj.name}" if grade_name else class_obj.name
            
            response_data = {
                "class_id": class_id,
                "class_name": class_obj.name,
                "class_full_name": class_full_name,
                "exam_id": exam_id,
                "exam_name": exam.name,
                "subject_count": 0,
                "total_students": len(students),
                "scored_students": 0,
                "completion_rate": 0,
                "subject_stats": {},
                "overall_stats": {},
                "top_students": [],
                "all_students": []
            }
        
        # 创建分析快照，用于历史记录
        snapshot_data = {
            "class_id": class_id,
            "exam_id": exam_id,
            "subject_id": subject_id,
            "timestamp": datetime.now().isoformat(),
            "stats": response_data
        }
        
        # 异步创建快照
        await AnalysisSnapshot.create(
            snapshot_type="class_scores",
            target_id=class_id,
            target_type="class",
            data=snapshot_data,
            exam_id=exam_id,
            subject_id=subject_id
        )
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级成绩分析成功",
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
            f"获取班级成绩分析失败: {str(e)}"
        )

@router.get("/class/{class_id}/history", response_model=StandardResponse, summary="获取班级历史成绩对比分析")
async def get_class_history(
    class_id: int,
    subject_id: int,
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取班级历史成绩对比分析
    
    - **class_id**: 班级ID
    - **subject_id**: 学科ID
    - **limit**: 最大考试数量（默认5，最多10）
    
    权限要求：
    - 学生：可以查看自己所在班级的历史成绩对比，需要班主任授权
    - 教师：可以查看自己任教班级和学科的历史成绩对比
    - 班主任：可以查看自己管理班级的历史成绩对比
    - 管理员：可以查看任何班级的历史成绩对比
    """
    try:
        # 检查用户是否有权限访问该班级数据
        await check_class_access(class_id, current_user)
        
        # 检查班级是否存在
        class_obj = await Class.get_or_none(id=class_id).prefetch_related("grade")
        if not class_obj:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{class_id}的班级"
            )
        
        # 检查考试是否存在
        exam = await Exam.get_or_none(id=subject_id)
        if not exam:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到ID为{subject_id}的考试"
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
        query = Score.filter(student_id__in=student_ids, exam_id=subject_id)
        
        # 获取成绩数据
        scores = await query.prefetch_related("student", "subject")
        
        if not scores:
            return create_error_response(
                status.HTTP_404_NOT_FOUND, 
                f"未找到该班级的历史成绩数据"
            )
        
        # 创建DataFrame进行分析
        data = []
        for score in scores:
            data.append({
                "student_id": score.student_id,
                "student_name": score.student.name,
                "student_code": score.student.student_code,
                "subject_id": score.subject_id,
                "subject_name": score.subject.name,
                "score": score.score,
                "exam_id": score.exam_id
            })
        
        df = pd.DataFrame(data)
        
        # 计算统计数据
        total_students = len(students)
        scored_students = df["student_id"].nunique()
        completion_rate = round(scored_students * 100 / total_students, 2) if total_students > 0 else 0
        
        # 按学科分组计算统计数据
        subject_stats = {}
        if not df.empty:
            subject_groups = df.groupby("subject_name")
            
            for subject_name, group in subject_groups:
                # 基本统计
                avg_score = round(group["score"].mean(), 2)
                max_score = group["score"].max()
                min_score = group["score"].min()
                count = len(group)
                std_dev = round(group["score"].std(), 2) if len(group) > 1 else 0
                
                # 考试成绩趋势
                exam_scores = []
                for _, row in group.sort_values("exam_date").iterrows():
                    exam_scores.append({
                        "exam_id": row["exam_id"],
                        "exam_name": row["exam_name"],
                        "exam_date": row["exam_date"],
                        "score": row["score"],
                        "ranking": row["ranking"] if pd.notna(row["ranking"]) else None
                    })
                
                # 计算进步情况
                progress = None
                if len(exam_scores) >= 2:
                    first_score = exam_scores[0]["score"]
                    last_score = exam_scores[-1]["score"]
                    progress = {
                        "first_score": first_score,
                        "last_score": last_score,
                        "change": round(last_score - first_score, 2),
                        "percent_change": round((last_score - first_score) * 100 / first_score, 2) if first_score > 0 else None
                    }
                
                subject_stats[subject_name] = {
                    "average_score": avg_score,
                    "max_score": max_score,
                    "min_score": min_score,
                    "standard_deviation": std_dev,
                    "exam_count": count,
                    "exam_scores": exam_scores,
                    "progress": progress
                }
        
        # 总体成绩统计
        overall_stats = {
            "average_score": round(df["score"].mean(), 2),
            "max_score": df["score"].max(),
            "min_score": df["score"].min(),
            "standard_deviation": round(df["score"].std(), 2) if len(df) > 1 else 0,
            "total_exams": df["exam_id"].nunique(),
            "total_subjects": df["subject_id"].nunique(),
            "total_scores": len(df)
        }
        
        # 获取班级信息
        class_name = class_obj.name
        grade_name = class_obj.grade.name if class_obj.grade else ""
        class_full_name = f"{grade_name}{class_name}" if grade_name else class_name
        
        # 构建响应
        response_data = {
            "class_id": class_id,
            "class_name": class_name,
            "class_full_name": class_full_name,
            "exam_id": subject_id,
            "exam_name": exam.name,
            "subject_count": len(subject_stats),
            "total_students": total_students,
            "scored_students": scored_students,
            "completion_rate": completion_rate,
            "subject_stats": subject_stats,
            "overall_stats": overall_stats
        }
        
        return StandardResponse(
            code=status.HTTP_200_OK,
            message="获取班级历史成绩对比分析成功",
            data=response_data,
            timestamp=datetime.now()
        )
    except HTTPException as e:
        return create_error_response(e.status_code, e.detail)
    except Exception as e:
        return create_error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"获取班级历史成绩对比分析失败: {str(e)}"
        )
