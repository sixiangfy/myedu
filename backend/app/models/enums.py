from enum import Enum

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"    # 管理员
    HEADTEACHER = "headteacher"  # 班主任
    TEACHER = "teacher"  # 教师
    STUDENT = "student"  # 学生 