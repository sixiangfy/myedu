from fastapi import APIRouter

from app.api.v1.endpoints import users, auth, scores, classes, exams, grades, subjects, students, teachers, analytics

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(scores.router, prefix="/scores", tags=["成绩管理"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["成绩分析"])
api_router.include_router(students.router, prefix="/students", tags=["学生管理"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["教师管理"])
api_router.include_router(classes.router, prefix="/classes", tags=["班级管理"]) 
api_router.include_router(exams.router, prefix="/exams", tags=["考试管理"])
api_router.include_router(grades.router, prefix="/grades", tags=["年级管理"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["科目管理"])

# 以下路由未实现，临时注释掉
# api_router.include_router(courses.router, prefix="/courses", tags=["课程管理"])
# api_router.include_router(reports.router, prefix="/reports", tags=["报表管理"])
# api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
# api_router.include_router(notifications.router, prefix="/notifications", tags=["通知管理"])

