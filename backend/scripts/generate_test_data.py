#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 只有显式运行 python -m scripts.generate_test_data 时，数据库才会被清空并重新生成
# 如果想保留现有数据并添加新数据，可以使用 python -m scripts.generate_test_data --keep-data

import asyncio
import random
import datetime
import argparse
from typing import List, Dict, Tuple, Optional
import numpy as np
from faker import Faker
from pathlib import Path
import sys
import os
import logging
from passlib.context import CryptContext
import traceback

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 导入应用模块
from app.core.config import settings
from app.db.init_db import init_db, close_db_connections
from app.models.user import User
from app.models.enums import UserRole
from app.models.grade import Grade
from app.models.class_model import Class
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.exam import Exam
from app.models.score import Score
from tortoise import Tortoise
from tortoise.exceptions import OperationalError, DoesNotExist

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("数据生成")

# 创建Faker实例
fake = Faker(['zh_CN'])

# 密码Hash上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 科目定义
SUBJECTS = {
    "语文": {"code": "CHN", "max_score": 120},
    "数学": {"code": "MATH", "max_score": 120},
    "英语": {"code": "ENG", "max_score": 120},
    "物理": {"code": "PHY", "max_score": 70},
    "化学": {"code": "CHEM", "max_score": 50},
    "政治": {"code": "POL", "max_score": 50},
    "历史": {"code": "HIST", "max_score": 50},
    "地理": {"code": "GEO", "max_score": 50},
    "生物": {"code": "BIO", "max_score": 50},
    "音乐": {"code": "MUS", "max_score": 100},
    "体育": {"code": "PE", "max_score": 100},
    "美术": {"code": "ART", "max_score": 100},
}

# 哪些年级开设哪些科目
GRADE_SUBJECTS = {
    "初一": ["语文", "数学", "英语", "政治", "历史", "地理", "生物", "音乐", "体育", "美术"],
    "初二": ["语文", "数学", "英语", "物理", "政治", "历史", "地理", "生物", "音乐", "体育", "美术"],
    "初三": ["语文", "数学", "英语", "物理", "化学", "政治", "历史", "地理", "生物", "音乐", "体育", "美术"],
}

# 考试类型
EXAM_TYPES = ["月考", "期中", "期末"]

# 生成密码哈希
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 生成正态分布的分数
def generate_normal_score(mean: float, std_dev: float, min_score: float, max_score: float) -> float:
    score = np.random.normal(mean, std_dev)
    return max(min(round(score, 1), max_score), min_score)

async def create_admin_user() -> User:
    """创建管理员账号"""
    logger.info("创建管理员账号")
    
    try:
        # 检查管理员是否已存在
        admin = await User.filter(username="admin").first()
        if admin:
            logger.info("管理员账号已存在，跳过创建")
            return admin
            
        # 创建管理员账号
        admin = await User.create(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            email="admin@example.com",
            phone="13800000000",
            is_active=True
        )
        
        logger.info(f"已创建管理员账号: {admin.username}")
        return admin
    except Exception as e:
        logger.error(f"创建管理员账号失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_subjects() -> Dict[str, Subject]:
    """创建学科数据"""
    logger.info("创建学科数据")
    
    subjects = {}
    try:
        for name, info in SUBJECTS.items():
            subject, created = await Subject.get_or_create(
                code=info["code"],
                defaults={
                    "name": name,
                    "description": f"{name}学科"
                }
            )
            subjects[name] = subject[0] if isinstance(subject, tuple) else subject
            if created:
                logger.info(f"已创建学科: {name}")
            else:
                logger.info(f"学科已存在: {name}")
        
        logger.info(f"共有{len(subjects)}个学科")
        return subjects
    except Exception as e:
        logger.error(f"创建学科数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_grades() -> Dict[str, Grade]:
    """创建年级数据"""
    logger.info("创建年级数据")
    
    grades = {}
    try:
        grade_names = ["初一", "初二", "初三"]
        for i, name in enumerate(grade_names, 1):
            enrollment_year = 2023 - (3 - i)
            code = f"{enrollment_year}级"
            
            grade, created = await Grade.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"{code}{name}"
                }
            )
            grades[name] = grade[0] if isinstance(grade, tuple) else grade
            if created:
                logger.info(f"已创建年级: {name}")
            else:
                logger.info(f"年级已存在: {name}")
        
        logger.info(f"共有{len(grades)}个年级")
        return grades
    except Exception as e:
        logger.error(f"创建年级数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_teachers(subjects: Dict[str, Subject]) -> Dict[str, List[Teacher]]:
    """创建教师数据"""
    logger.info("创建教师数据")
    
    # 按学科分组的教师列表
    teachers_by_subject = {subject_name: [] for subject_name in SUBJECTS.keys()}
    
    try:
        # 定义每个学科需要的教师数量 - 确保有足够的教师可以分配给所有班级
        # 按照每个年级10个班计算，共30个班级
        teacher_counts = {
            "语文": 40,  # 每个班都需要语文老师
            "数学": 40,  # 每个班都需要数学老师
            "英语": 40,  # 每个班都需要英语老师
            "物理": 25,  # 初二和初三开设，共20个班
            "化学": 15,  # 只有初三开设，共10个班
            "政治": 20,  # 所有年级开设
            "历史": 20,  # 所有年级开设
            "地理": 20,  # 所有年级开设
            "生物": 20,  # 所有年级开设
            "音乐": 15,  # 专业课教师可以跨多个班级
            "体育": 15,  # 专业课教师可以跨多个班级
            "美术": 15,  # 专业课教师可以跨多个班级
        }
        
        # 为每个学科创建教师
        for subject_name, subject_obj in subjects.items():
            count = teacher_counts.get(subject_name, 10)  # 默认至少10名教师
            
            for i in range(1, count + 1):
                # 生成教师编号: 学科代码 + 序号
                teacher_code = f"{subject_obj.code}{i:03d}"
                
                # 创建教师用户账号
                username = f"t_{teacher_code.lower()}"
                
                # 检查用户是否已存在
                existing_user = await User.filter(username=username).first()
                if existing_user:
                    user_id = existing_user.id
                    user_created = False
                else:
                    # 创建新用户
                    new_user = await User.create(
                        username=username,
                        hashed_password=get_password_hash(f"pass_{username}"),
                        role=UserRole.TEACHER,
                        email=f"{username}@example.com",
                        phone=fake.phone_number(),
                        is_active=True
                    )
                    user_id = new_user.id
                    user_created = True
                
                # 检查教师是否已存在
                existing_teacher = await Teacher.filter(teacher_code=teacher_code).first()
                if existing_teacher:
                    teacher_obj = existing_teacher
                    teacher_created = False
                else:
                    # 创建新教师
                    teacher_obj = await Teacher.create(
                        teacher_code=teacher_code,
                        name=fake.name(),
                        phone=fake.phone_number(),
                        email=f"{username}@example.com",
                        user_id=user_id,
                        subject_id=subject_obj.id
                    )
                    teacher_created = True
                
                # 将教师添加到对应学科的列表
                teachers_by_subject[subject_name].append(teacher_obj)
                
                if teacher_created or user_created:
                    logger.info(f"已创建 {subject_name} 教师: {teacher_obj.name} ({teacher_code})")
                else:
                    logger.info(f"{subject_name} 教师已存在: {teacher_obj.name} ({teacher_code})")
        
        # 为每个学科记录教师数量
        for subject, teachers in teachers_by_subject.items():
            logger.info(f"共有 {subject} 教师 {len(teachers)} 名")
        
        return teachers_by_subject
    except Exception as e:
        logger.error(f"创建教师数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_classes(grades: Dict[str, Grade], teachers_by_subject: Dict[str, List[Teacher]]) -> Dict[str, List[Class]]:
    """创建班级数据"""
    logger.info("创建班级数据")
    
    classes_by_grade = {grade_name: [] for grade_name in grades.keys()}
    
    try:
        # 每个年级的班级数量
        class_counts = {
            "初一": 10,
            "初二": 10,
            "初三": 10,
        }
        
        # 记录已经被分配为班主任的教师
        assigned_headteachers = set()
        # 记录教师已经被分配的班级数，用于均衡教师工作量
        teacher_class_counts = {}
        
        # 为每个年级创建班级
        for grade_name, grade_obj in grades.items():
            count = class_counts.get(grade_name, 10)
            enrollment_year = grade_obj.code.replace("级", "")
            grade_subjects = GRADE_SUBJECTS[grade_name]
            
            # 预筛选该年级可用的教师
            available_teachers_by_subject = {}
            for subject_name in grade_subjects:
                # 主科教师选择工作量较小的教师优先分配
                subject_teachers = teachers_by_subject.get(subject_name, [])
                if subject_teachers:
                    # 根据已分配班级数排序教师
                    sorted_teachers = sorted(
                        subject_teachers,
                        key=lambda t: teacher_class_counts.get(t.id, 0)
                    )
                    available_teachers_by_subject[subject_name] = sorted_teachers
            
            for i in range(1, count + 1):
                # 班级编号: 年级编号 + 2位序号
                class_code = f"{enrollment_year}{i:02d}"
                class_name = f"{i:02d}班"
                
                # 检查班级是否已存在
                existing_class = await Class.filter(code=class_code).first()
                
                if existing_class:
                    logger.info(f"班级已存在: {grade_name}{class_name} ({class_code})")
                    await existing_class.fetch_related("teachers")
                    classes_by_grade[grade_name].append(existing_class)
                    continue
                
                # 创建班级，先不设置班主任
                class_obj = await Class.create(
                    code=class_code,
                    name=class_name,
                    capacity=random.randint(40, 45),
                    grade_id=grade_obj.id,
                    headteacher_id=None  # 先不设置班主任
                )
                
                logger.info(f"已创建班级: {grade_name}{class_name} ({class_code})")
                
                # 分配任课教师 - 确保每个学科都有教师
                added_teachers = []
                for subject_name in grade_subjects:
                    if subject_name not in available_teachers_by_subject or not available_teachers_by_subject[subject_name]:
                        logger.warning(f"没有可用的{subject_name}教师分配给班级{class_code}")
                        continue
                    
                    # 按工作量选择教师
                    subject_teachers = available_teachers_by_subject[subject_name]
                    selected_teacher = None
                    
                    # 尝试找到工作量最少的教师
                    for teacher in subject_teachers:
                        if teacher_class_counts.get(teacher.id, 0) < 6:  # 限制每个教师最多教6个班
                            selected_teacher = teacher
                            break
                    
                    # 如果没有找到合适的教师，就选择第一个可用的
                    if not selected_teacher and subject_teachers:
                        selected_teacher = subject_teachers[0]
                    
                    if selected_teacher:
                        # 建立班级与教师的关联
                        await class_obj.teachers.add(selected_teacher)
                        
                        # 更新教师工作量计数
                        teacher_class_counts[selected_teacher.id] = teacher_class_counts.get(selected_teacher.id, 0) + 1
                        
                        # 将任课教师添加到班主任候选人列表，并同时预先获取subject对象
                        if selected_teacher.id not in assigned_headteachers:
                            # 确保加载教师的学科信息
                            await selected_teacher.fetch_related("subject")
                            added_teachers.append(selected_teacher)
                            
                        logger.info(f"为班级 {class_code} 分配{subject_name}教师: {selected_teacher.name}")
                
                # 优先从语文、数学、英语教师中选择班主任
                potential_headteachers = [t for t in added_teachers if hasattr(t, 'subject') and t.subject.name in ["语文", "数学", "英语"]]
                
                # 如果没有主科教师可用，则从所有添加的教师中选择
                if not potential_headteachers:
                    potential_headteachers = added_teachers
                
                # 从候选班主任中选择工作量较少的一位
                if potential_headteachers:
                    potential_headteachers.sort(key=lambda t: teacher_class_counts.get(t.id, 0))
                    headteacher = potential_headteachers[0]
                    
                    # 标记该教师为班主任，避免一人同时担任多个班的班主任
                    assigned_headteachers.add(headteacher.id)
                    
                    # 设置班主任
                    class_obj.headteacher_id = headteacher.id
                    await class_obj.save()
                    
                    # 更新教师角色为班主任
                    try:
                        user = await User.get(id=headteacher.user_id)
                        user.role = UserRole.HEADTEACHER
                        await user.save()
                        logger.info(f"已为班级 {class_code} 设置班主任: {headteacher.name}")
                    except DoesNotExist:
                        logger.warning(f"找不到教师用户 ID: {headteacher.user_id}")
                else:
                    logger.warning(f"班级 {class_code} 没有可用的班主任候选人")
                
                classes_by_grade[grade_name].append(class_obj)
            
            logger.info(f"共有 {grade_name} 班级 {len(classes_by_grade[grade_name])} 个")
        
        # 检查班级是否都有班主任和足够的任课教师
        for grade_name, classes in classes_by_grade.items():
            grade_subjects = GRADE_SUBJECTS[grade_name]
            for class_obj in classes:
                await class_obj.fetch_related("teachers")
                
                # 检查班主任
                if not class_obj.headteacher_id:
                    logger.warning(f"警告: 班级 {class_obj.code} 没有班主任")
                
                # 检查任课教师是否覆盖所有学科
                subject_coverage = set()
                for teacher in class_obj.teachers:
                    # 确保加载教师的学科信息
                    await teacher.fetch_related("subject")
                    subject_coverage.add(teacher.subject.name)
                
                missing_subjects = set(grade_subjects) - subject_coverage
                if missing_subjects:
                    logger.warning(f"警告: 班级 {class_obj.code} 缺少以下学科的任课教师: {', '.join(missing_subjects)}")
        
        return classes_by_grade
    except Exception as e:
        logger.error(f"创建班级数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_students(classes_by_grade: Dict[str, List[Class]]) -> Dict[str, List[Student]]:
    """创建学生数据"""
    logger.info("创建学生数据")
    
    students_by_class = {}
    total_students = 0
    
    try:
        # 为每个班级创建学生
        for grade_name, classes in classes_by_grade.items():
            for class_obj in classes:
                student_count = class_obj.capacity
                students = []
                
                # 入学年份
                enrollment_year = class_obj.code[:4]
                
                logger.info(f"开始为班级 {class_obj.code}(ID={class_obj.id}) 创建学生")
                
                # 首先尝试获取班级的表结构，了解确切的字段名
                try:
                    conn = Tortoise.get_connection("default")
                    table_info = await conn.execute_query("SHOW COLUMNS FROM students")
                    logger.info(f"学生表字段: {[col[0] for col in table_info[1]]}")
                except Exception as e:
                    logger.error(f"获取表结构失败: {str(e)}")
                
                for i in range(1, student_count + 1):
                    # 学号: 班级编号 + 2位序号
                    student_code = f"{class_obj.code}{i:02d}"
                    
                    # 检查学生是否已存在
                    existing_student = await Student.filter(student_code=student_code).first()
                    if existing_student:
                        logger.info(f"学生 {student_code} 已存在，跳过创建")
                        students.append(existing_student)
                        continue
                    
                    # 创建学生用户账号
                    username = f"s_{student_code.lower()}"
                    user, user_created = await User.get_or_create(
                        username=username,
                        defaults={
                            "hashed_password": get_password_hash(f"pass_{username}"),
                            "role": UserRole.STUDENT,
                            "email": f"{username}@example.com",
                            "phone": fake.phone_number(),
                            "is_active": True
                        }
                    )
                    
                    user_id = user[0].id if isinstance(user, tuple) else user.id
                    
                    # 创建学生信息
                    gender = random.choice(["男", "女"])
                    birth_date = fake.date_of_birth(minimum_age=11, maximum_age=14)
                    
                    # 重试创建学生，最多尝试3次
                    max_retries = 3
                    student = None
                    
                    for retry in range(max_retries):
                        try:
                            # 尝试使用ORM创建，确保字段名对应
                            student = await Student.create(
                                student_code=student_code,
                                name=fake.name_male() if gender == "男" else fake.name_female(),
                                gender=gender,
                                birth_date=birth_date,
                                address=fake.address(),
                                phone=fake.phone_number(),
                                parent_name=fake.name(),
                                parent_phone=fake.phone_number(),
                                user_id=user_id,
                                class_field=class_obj  # 使用class对象，而不是ID
                            )
                            
                            students.append(student)
                            
                            if i % 10 == 0:  # 只记录每10个学生，以减少日志量
                                logger.info(f"已创建学生: {student.name} ({student_code})")
                            
                            break  # 创建成功，跳出重试循环
                            
                        except Exception as e:
                            error_message = str(e)
                            logger.error(f"使用ORM创建学生失败: {error_message}")
                            
                            # 如果重试失败，回退到使用原始SQL
                            if retry == max_retries - 1:
                                try:
                                    # 直接通过SQL创建学生记录，确保列名与数据库表一致
                                    conn = Tortoise.get_connection("default")
                                    
                                    # 准备插入数据
                                    student_name = fake.name_male() if gender == "男" else fake.name_female()
                                    student_address = fake.address()
                                    student_phone = fake.phone_number()
                                    parent_name = fake.name()
                                    parent_phone = fake.phone_number()
                                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    # 将日期转为字符串
                                    birth_date_str = birth_date.strftime("%Y-%m-%d") if birth_date else None
                                    
                                    # 执行SQL插入，注意应该使用column_id而不是id用于自增主键
                                    student_id = await conn.execute_query(
                                        """
                                        INSERT INTO students (
                                            student_code, name, gender, birth_date, address, 
                                            phone, parent_name, parent_phone, user_id, class_id,
                                            created_at, updated_at
                                        ) VALUES (
                                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                        ) RETURNING id
                                        """,
                                        [
                                            student_code, student_name, gender, birth_date_str, 
                                            student_address, student_phone, parent_name, parent_phone,
                                            user_id, class_obj.id, now, now
                                        ]
                                    )
                                    
                                    # 创建成功后，获取学生记录
                                    student = await Student.get(id=student_id[1])
                                    students.append(student)
                                    
                                    if i % 10 == 0:  # 只记录每10个学生，以减少日志量
                                        logger.info(f"已通过SQL创建学生: {student.name} ({student_code})")
                                        
                                except Exception as sql_error:
                                    logger.error(f"通过SQL创建学生 {student_code} 失败: {str(sql_error)}")
                            else:
                                if retry < max_retries - 1:
                                    logger.warning(f"创建学生 {student_code} 失败，尝试重试 ({retry+1}/{max_retries}): {error_message}")
                                    await asyncio.sleep(0.5)  # 稍微延迟后重试
                    
                    if not student:
                        logger.error(f"无法创建学生 {student_code}，跳过")
                        continue
                
                students_by_class[class_obj.code] = students
                total_students += len(students)
                logger.info(f"班级 {class_obj.code} 共有学生 {len(students)} 名")
        
        logger.info(f"总共创建学生 {total_students} 名")
        return students_by_class
    except Exception as e:
        logger.error(f"创建学生数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_exams(grades: Dict[str, Grade], subjects: Dict[str, Subject]) -> Dict[str, List[Exam]]:
    """创建考试数据"""
    logger.info("创建考试数据")
    
    exams_by_grade = {grade_name: [] for grade_name in grades.keys()}
    # 用于跟踪相同考试的不同科目
    exam_groups = {}
    
    try:
        # 定义三个学年的考试
        academic_years = [
            # 2020-2021学年
            {
                "start_date": datetime.datetime(2020, 9, 1),
                "end_date": datetime.datetime(2021, 7, 15),
                "monthly_exams": [
                    # 月考时间
                    datetime.datetime(2020, 9, 20),
                    datetime.datetime(2020, 10, 25),
                    datetime.datetime(2020, 12, 5),
                    datetime.datetime(2021, 3, 15),
                    datetime.datetime(2021, 5, 10),
                    datetime.datetime(2021, 6, 5),
                ],
                "midterms": [
                    # 期中考试
                    datetime.datetime(2020, 11, 10),
                    datetime.datetime(2021, 4, 15),
                ],
                "finals": [
                    # 期末考试
                    datetime.datetime(2021, 1, 15),
                    datetime.datetime(2021, 7, 1),
                ]
            },
            # 2021-2022学年
            {
                "start_date": datetime.datetime(2021, 9, 1),
                "end_date": datetime.datetime(2022, 7, 15),
                "monthly_exams": [
                    datetime.datetime(2021, 9, 25),
                    datetime.datetime(2021, 10, 20),
                    datetime.datetime(2021, 12, 10),
                    datetime.datetime(2022, 3, 10),
                    datetime.datetime(2022, 5, 15),
                    datetime.datetime(2022, 6, 10),
                ],
                "midterms": [
                    datetime.datetime(2021, 11, 5),
                    datetime.datetime(2022, 4, 20),
                ],
                "finals": [
                    datetime.datetime(2022, 1, 10),
                    datetime.datetime(2022, 7, 5),
                ]
            },
            # 2022-2023学年
            {
                "start_date": datetime.datetime(2022, 9, 1),
                "end_date": datetime.datetime(2023, 7, 15),
                "monthly_exams": [
                    datetime.datetime(2022, 9, 15),
                    datetime.datetime(2022, 10, 20),
                    datetime.datetime(2022, 12, 15),
                    datetime.datetime(2023, 3, 20),
                    datetime.datetime(2023, 5, 20),
                    datetime.datetime(2023, 6, 15),
                ],
                "midterms": [
                    datetime.datetime(2022, 11, 15),
                    datetime.datetime(2023, 4, 25),
                ],
                "finals": [
                    datetime.datetime(2023, 1, 15),
                    datetime.datetime(2023, 7, 10),
                ]
            }
        ]
        
        # 为每个年级创建考试
        for grade_name, grade_obj in grades.items():
            # 获取该年级的科目
            grade_subject_list = GRADE_SUBJECTS[grade_name]
            grade_subjects = [subjects[subject_name] for subject_name in grade_subject_list 
                             if subject_name in subjects and subject_name not in ["音乐", "体育", "美术"]]
            
            # 考试计数器
            exam_counter = 0
            
            # 为每个学年创建考试
            for year_index, academic_year in enumerate(academic_years):
                # 年级年份调整 (如初一在第一年, 初二在第二年, 初三在第三年)
                if grade_name == "初一" and year_index > 0:
                    continue
                if grade_name == "初二" and (year_index == 0 or year_index == 2):
                    continue
                if grade_name == "初三" and year_index < 2:
                    continue
                
                # 创建月考
                for exam_date in academic_year["monthly_exams"]:
                    date_str = exam_date.strftime('%Y-%m-%d')
                    exam_base_name = f"{date_str}_月考_{grade_name}"
                    # 为所有科目创建一个统一的考试ID
                    exam_id = f"{date_str}_{grade_name}_月考"
                    await create_exam_group(exam_base_name, exam_id, exam_date, grade_subjects, exams_by_grade, grade_name, exam_groups)
                    exam_counter += 1
                
                # 创建期中考试
                for exam_date in academic_year["midterms"]:
                    date_str = exam_date.strftime('%Y-%m-%d')
                    exam_base_name = f"{date_str}_期中_{grade_name}"
                    exam_id = f"{date_str}_{grade_name}_期中"
                    await create_exam_group(exam_base_name, exam_id, exam_date, grade_subjects, exams_by_grade, grade_name, exam_groups)
                    exam_counter += 1
                
                # 创建期末考试
                for exam_date in academic_year["finals"]:
                    date_str = exam_date.strftime('%Y-%m-%d')
                    exam_base_name = f"{date_str}_期末_{grade_name}"
                    exam_id = f"{date_str}_{grade_name}_期末"
                    await create_exam_group(exam_base_name, exam_id, exam_date, grade_subjects, exams_by_grade, grade_name, exam_groups)
                    exam_counter += 1
                
                # 添加单元测试 (每学期2-3次)
                unit_test_dates = []
                # 第一学期单元测试
                for month in range(9, 12):
                    if random.random() < 0.7:  # 70%概率有单元测试
                        day = random.randint(5, 25)
                        unit_test_dates.append(datetime.datetime(academic_year["start_date"].year, month, day))
                
                # 第二学期单元测试
                for month in range(2, 6):
                    if random.random() < 0.7:  # 70%概率有单元测试
                        day = random.randint(5, 25)
                        unit_test_dates.append(datetime.datetime(academic_year["end_date"].year, month, day))
                
                # 创建单元测试
                for i, exam_date in enumerate(unit_test_dates):
                    date_str = exam_date.strftime('%Y-%m-%d')
                    exam_base_name = f"{date_str}_单元测试{i+1}_{grade_name}"
                    exam_id = f"{date_str}_{grade_name}_单元测试{i+1}"
                    
                    # 单元测试随机选择2-3个主科
                    main_subjects = [s for s in grade_subjects if s.name in ["语文", "数学", "英语", "物理", "化学"]]
                    if main_subjects:
                        selected_subjects = random.sample(
                            main_subjects, 
                            min(random.randint(2, 3), len(main_subjects))
                        )
                        await create_exam_group(exam_base_name, exam_id, exam_date, selected_subjects, exams_by_grade, grade_name, exam_groups)
                        exam_counter += 1
            
            logger.info(f"为 {grade_name} 创建了 {exam_counter} 次考试，共 {len(exams_by_grade[grade_name])} 个考试-科目记录")
            logger.info(f"为 {grade_name} 创建了 {len(exam_groups)} 个考试组")
        
        return exams_by_grade
    except Exception as e:
        logger.error(f"创建考试数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def create_exam_group(exam_base_name, exam_id, exam_date, subjects, exams_by_grade, grade_name, exam_groups):
    """为一次考试创建多个科目的考试记录，共享同一个exam_id"""
    
    # 如果这个考试ID还没有被创建，初始化一个列表
    if exam_id not in exam_groups:
        exam_groups[exam_id] = []
    
    for subject in subjects:
        # 跳过音体美
        if subject.name in ["音乐", "体育", "美术"]:
            continue
            
        total_score = SUBJECTS[subject.name]["max_score"]
        
        # 创建考试
        exam, created = await Exam.get_or_create(
            name=exam_base_name,
            subject_id=subject.id,
            defaults={
                "exam_date": exam_date,
                "description": f"{grade_name} {exam_base_name.split('_')[1]} {subject.name}考试",
                "total_score": total_score,
                "exam_id": exam_id  # 使用统一的考试ID
            }
        )
        
        exam = exam[0] if isinstance(exam, tuple) else exam
        
        # 更新exam_id字段，确保即使是已存在的考试也有正确的exam_id
        if created:
            logger.info(f"已创建考试: {exam_base_name} - {subject.name}")
        else:
            # 对于已存在的考试，可能需要更新exam_id
            if not hasattr(exam, 'exam_id') or exam.exam_id != exam_id:
                exam.exam_id = exam_id
                await exam.save()
            logger.info(f"已更新考试ID: {exam_base_name} - {subject.name}")
        
        # 将考试添加到年级的考试列表和考试组
        exams_by_grade[grade_name].append(exam)
        exam_groups[exam_id].append(exam)
    
    return

async def create_scores(
    exams_by_grade: Dict[str, List[Exam]], 
    students_by_class: Dict[str, List[Student]], 
    classes_by_grade: Dict[str, List[Class]], 
    subjects: Dict[str, Subject]
) -> None:
    """创建成绩数据"""
    logger.info("创建成绩数据")
    
    total_scores = 0
    
    try:
        # 为每个年级的每个考试创建成绩
        for grade_name, exams in exams_by_grade.items():
            # 获取该年级的所有班级和学生
            grade_classes = classes_by_grade[grade_name]
            all_grade_students = []
            
            # 汇总该年级所有学生
            for class_obj in grade_classes:
                students = students_by_class.get(class_obj.code, [])
                if students:
                    all_grade_students.extend(students)
            
            logger.info(f"{grade_name}年级共有学生 {len(all_grade_students)} 名")
            
            if not all_grade_students:
                logger.warning(f"{grade_name}年级没有学生，跳过成绩生成")
                continue
            
            # 定义该年级考试参与的科目
            grade_subject_list = GRADE_SUBJECTS[grade_name]
            grade_subject_objs = {name: subjects[name] for name in grade_subject_list if name in subjects and name not in ["音乐", "体育", "美术"]}
            
            # 考试汇总信息
            total_exams_count = 0
            
            # 按exam_id组织考试
            exam_groups = {}
            for exam in exams:
                if exam.exam_id:
                    if exam.exam_id not in exam_groups:
                        exam_groups[exam.exam_id] = []
                    exam_groups[exam.exam_id].append(exam)
            
            logger.info(f"{grade_name}年级共有 {len(exam_groups)} 个考试组")
            
            # 处理每个考试组
            for exam_id, group_exams in exam_groups.items():
                # 获取第一个考试的日期作为考试组日期
                if not group_exams:
                    continue
                    
                exam_date = group_exams[0].exam_date
                exam_type = group_exams[0].name.split('_')[1]  # 月考/期中/期末/单元测试
                
                exam_label = f"{exam_date.strftime('%Y-%m-%d')}_{exam_type}"
                logger.info(f"正在为{grade_name}创建 {exam_label} 考试成绩，共{len(group_exams)}个科目")
                
                # 从所有该年级学生中随机选择3-10%完全缺考的学生
                full_absent_rate = random.uniform(0.03, 0.10)
                fully_absent_students = set(random.sample(all_grade_students, int(len(all_grade_students) * full_absent_rate)))
                logger.info(f"有 {len(fully_absent_students)} 名学生完全缺考 {exam_label}")
                
                # 按班级组织学生
                students_by_class_id = {}
                for student in all_grade_students:
                    if student.class_field_id not in students_by_class_id:
                        students_by_class_id[student.class_field_id] = []
                    students_by_class_id[student.class_field_id].append(student)
                
                # 对每个科目依次创建成绩
                for exam in group_exams:
                    # 获取科目对象
                    subject_id = exam.subject_id
                    subject = await Subject.get(id=subject_id)
                    subject_name = subject.name
                    
                    # 检查该考试成绩是否已存在
                    existing_scores = await Score.filter(
                        exam_id=exam.id,
                        subject_id=subject_id
                    ).count()
                    
                    if existing_scores > 0:
                        logger.info(f"{exam.name} - {subject_name} 考试成绩已存在 {existing_scores} 条记录，跳过")
                        continue
                    
                    total_exams_count += 1
                    
                    # 确定该科目满分
                    max_score = SUBJECTS.get(subject_name, {"max_score": 100})["max_score"]
                    
                    # 按班级生成成绩，确保班级间有一定差异
                    all_scores_to_create = []
                    
                    for class_id, class_students in students_by_class_id.items():
                        # 为每个班级设置略有不同的平均分和标准差，以体现班级差异
                        class_factor = random.uniform(0.9, 1.1)  # 班级整体水平因子
                        
                        # 设置不同科目的平均分和标准差
                        if subject_name in ["语文", "数学", "英语"]:
                            mean_score = max_score * 0.7 * class_factor  # 平均分为满分的70%左右
                            std_dev = max_score * 0.15    # 标准差为满分的15%
                        elif subject_name in ["物理", "化学"]:
                            mean_score = max_score * 0.65 * class_factor
                            std_dev = max_score * 0.18
                        else:  # 文科
                            mean_score = max_score * 0.75 * class_factor
                            std_dev = max_score * 0.12
                        
                        # 除了完全缺考的学生外，再随机选择2-5%的学生对该科目缺考
                        subject_absent_rate = random.uniform(0.02, 0.05)
                        available_students = [s for s in class_students if s not in fully_absent_students]
                        subject_absent_count = int(len(available_students) * subject_absent_rate)
                        subject_absent_students = set(random.sample(available_students, subject_absent_count)) if available_students else set()
                        
                        # 所有缺考学生
                        absent_students = fully_absent_students.union(subject_absent_students)
                        
                        # 为非缺考学生创建成绩
                        class_scores = []
                        for student in class_students:
                            # 如果学生缺考，则跳过
                            if student in absent_students:
                                continue
                            
                            # 生成分数，确保有一定比例的优秀和不及格
                            if random.random() < 0.05:  # 5%概率出现极端值
                                if random.random() < 0.7:  # 极端值中70%为高分
                                    score_value = random.uniform(max_score * 0.95, max_score)
                                else:  # 30%为低分
                                    score_value = random.uniform(0, max_score * 0.3)
                            else:  # 95%概率是正态分布的分数
                                score_value = generate_normal_score(
                                    mean_score, std_dev, 0, max_score
                                )
                            
                            # 创建成绩记录
                            score = Score(
                                score=round(score_value, 1),
                                ranking=None,  # 排名后计算
                                comments=None,
                                student_id=student.id,
                                subject_id=subject_id,
                                exam_id=exam.id
                            )
                            class_scores.append(score)
                        
                        # 如果该班有成绩，计算排名
                        if class_scores:
                            # 按分数排序
                            class_scores.sort(key=lambda s: s.score, reverse=True)
                            
                            # 设置排名
                            for rank, score in enumerate(class_scores, 1):
                                score.ranking = rank
                                
                                # 为前三名和后三名添加评语
                                if rank <= 3:
                                    score.comments = random.choice([
                                        "表现优秀，继续保持！",
                                        "成绩出色，希望再接再厉！",
                                        "优异的成绩，值得表扬！"
                                    ])
                                elif rank >= len(class_scores) - 2:
                                    score.comments = random.choice([
                                        "需要加强学习，提高成绩",
                                        "请认真复习，查漏补缺",
                                        "建议多做练习，巩固知识点"
                                    ])
                            
                            # 添加到总列表
                            all_scores_to_create.extend(class_scores)
                    
                    # 批量创建成绩
                    if all_scores_to_create:
                        try:
                            created_scores = await Score.bulk_create(all_scores_to_create)
                            total_scores += len(created_scores)
                            logger.info(f"{exam.name} - {subject_name} 创建了 {len(created_scores)} 条成绩")
                        except Exception as bulk_error:
                            logger.error(f"批量创建成绩失败: {str(bulk_error)}")
                            # 尝试逐条创建
                            success_count = 0
                            for score in all_scores_to_create:
                                try:
                                    await score.save()
                                    success_count += 1
                                except Exception as single_error:
                                    pass
                            total_scores += success_count
                            logger.info(f"{exam.name} - {subject_name} 逐条创建了 {success_count} 条成绩")
            
            logger.info(f"{grade_name}年级共完成 {total_exams_count} 次考试科目成绩录入")
        
        logger.info(f"总共创建成绩记录 {total_scores} 条")
    except Exception as e:
        logger.error(f"创建成绩数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def main(reset_db=True):
    """
    主函数
    
    Args:
        reset_db: 是否重置数据库，默认为True
    """
    logger.info("开始生成测试数据")
    
    try:
        # 初始化数据库连接
        if reset_db:
            logger.info("初始化数据库并清空现有数据...")
            await init_db(generate_only=False)  # 使用generate_only=False，先删除现有表再创建
        else:
            logger.info("连接数据库，保留现有数据...")
            await init_db(generate_only=True)  # 使用generate_only=True，保留现有数据
        
        # 创建管理员账号
        admin = await create_admin_user()
        
        # 创建学科
        subjects = await create_subjects()
        
        # 创建年级
        grades = await create_grades()
        
        # 创建教师
        teachers_by_subject = await create_teachers(subjects)
        
        # 创建班级
        classes_by_grade = await create_classes(grades, teachers_by_subject)
        
        # 创建学生
        students_by_class = await create_students(classes_by_grade)
        
        # 创建考试
        exams_by_grade = await create_exams(grades, subjects)
        
        # 创建成绩
        await create_scores(exams_by_grade, students_by_class, classes_by_grade, subjects)
        
        logger.info("测试数据生成完成!")
    except Exception as e:
        logger.error(f"生成测试数据时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # 关闭数据库连接
        await close_db_connections()


if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="生成教务管理系统测试数据")
    parser.add_argument(
        "--keep-data", 
        action="store_true", 
        help="保留现有数据库数据，只添加新数据"
    )
    args = parser.parse_args()
    
    # 根据参数决定是否保留现有数据
    reset_db = not args.keep_data
    
    if reset_db:
        logger.info("将重置数据库(删除所有现有数据)")
    else:
        logger.info("将保留现有数据")
    
    # 运行主函数
    asyncio.run(main(reset_db=reset_db)) 