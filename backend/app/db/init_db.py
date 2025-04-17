import logging
import redis.asyncio as redis
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
import json

from app.core.config import settings
from app.models import TORTOISE_MODELS
from app.models.setting import Setting
from app.core.logging import get_db_logger

# 获取数据库日志记录器
db_logger = get_db_logger()

# Redis连接池
redis_pool = None


async def init_db(generate_only: bool = True) -> None:
    """
    初始化数据库和Redis连接
    
    Args:
        generate_only: 如果为True，只生成表结构而不删除现有表；如果为False，先删除再创建
    """
    # 初始化Tortoise-ORM
    await init_tortoise(generate_only=generate_only)
    
    # 初始化Redis
    await init_redis()
    
    # 初始化系统设置
    await init_settings()


async def drop_tables() -> None:
    """
    删除所有数据表
    """
    db_logger.info("尝试删除现有数据表...")
    
    table_names = [
        "users", "grades", "classes", "subjects", 
        "teachers", "students", "exams", "scores",
        "class_teacher", "settings", "notifications"  # m2m关系表
    ]
    
    for table in table_names:
        try:
            await Tortoise.get_connection("default").execute_query(f"DROP TABLE IF EXISTS {table}")
            db_logger.info(f"已删除表: {table}")
        except Exception as e:
            db_logger.error(f"删除表 {table} 失败: {str(e)}")


async def init_tortoise(generate_only: bool = True) -> None:
    """
    初始化Tortoise-ORM
    
    Args:
        generate_only: 如果为True，只生成表结构而不删除现有表；如果为False，先删除再创建
    """
    db_logger.info("正在初始化Tortoise-ORM...")
    
    # 使用MySQL连接
    await Tortoise.init(
        db_url=settings.DATABASE_URI,
        modules={"models": TORTOISE_MODELS},
    )
    
    # 如果不是仅生成模式，则先删除现有表
    if not generate_only:
        await drop_tables()
    
    # 生成数据库schema
    db_logger.info("正在生成数据库模式...")
    try:
        # 根据generate_only参数决定使用哪种方式生成schema
        if generate_only:
            # 使用safe=True只创建不存在的表
            await Tortoise.generate_schemas(safe=True)
            db_logger.info("数据库模式生成完成(安全模式，保留现有数据)")
        else:
            # 使用safe=False强制重新创建表
            await Tortoise.generate_schemas(safe=False)
            db_logger.info("数据库模式生成完成(强制模式，已清空数据)")
    except OperationalError as e:
        db_logger.error(f"生成数据库模式时出错: {str(e)}")
        # 尝试使用safe=True
        db_logger.info("尝试使用安全模式生成数据库模式...")
        await Tortoise.generate_schemas(safe=True)
        db_logger.info("数据库模式生成完成(安全模式)")
    
    db_logger.info("Tortoise-ORM初始化完成")


async def init_redis() -> None:
    """
    初始化Redis连接
    """
    global redis_pool
    
    db_logger.info("正在初始化Redis连接...")
    try:
        redis_url = settings.REDIS_URI
        db_logger.info(f"Redis连接URL: {redis_url}")
        redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True
        )
        # 测试连接
        test_conn = redis.Redis(connection_pool=redis_pool)
        await test_conn.ping()
        db_logger.info("Redis连接测试成功")
    except Exception as e:
        db_logger.error(f"Redis连接失败: {str(e)}")
        raise
    db_logger.info("Redis连接初始化完成")


async def init_settings() -> None:
    """
    初始化系统设置
    """
    db_logger.info("正在初始化系统设置...")
    
    # 默认系统设置
    default_settings = [
        {
            "key": "site_name",
            "value": "教育管理系统",
            "value_type": "string",
            "description": "网站名称",
            "group": "基础设置",
            "is_public": True,
            "is_system": True,
            "order": 100
        },
        {
            "key": "site_description",
            "value": "一个全面的教育管理解决方案",
            "value_type": "string",
            "description": "网站描述",
            "group": "基础设置",
            "is_public": True,
            "is_system": True,
            "order": 90
        },
        {
            "key": "admin_email",
            "value": "admin@example.com",
            "value_type": "string",
            "description": "管理员邮箱",
            "group": "基础设置",
            "is_public": False,
            "is_system": True,
            "order": 80
        },
        {
            "key": "allow_registration",
            "value": "true",
            "value_type": "boolean",
            "description": "是否允许新用户注册",
            "group": "用户设置",
            "is_public": True,
            "is_system": True,
            "order": 100
        },
        {
            "key": "score_decimal_places",
            "value": "1",
            "value_type": "number",
            "description": "成绩小数位数",
            "group": "成绩设置",
            "is_public": False,
            "is_system": True,
            "order": 100
        },
        {
            "key": "grade_levels",
            "value": json.dumps(["初一", "初二", "初三", "高一", "高二", "高三"]),
            "value_type": "json",
            "description": "系统支持的年级列表",
            "group": "基础设置",
            "is_public": True,
            "is_system": True,
            "order": 70
        },
        {
            "key": "default_subjects",
            "value": json.dumps(["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育", "音乐", "美术"]),
            "value_type": "json",
            "description": "默认科目列表",
            "group": "基础设置",
            "is_public": True,
            "is_system": True,
            "order": 60
        },
        {
            "key": "system_announcement",
            "value": "欢迎使用教育管理系统！",
            "value_type": "string",
            "description": "系统公告",
            "group": "内容设置",
            "is_public": True,
            "is_system": False,
            "order": 100
        },
        {
            "key": "maintenance_mode",
            "value": "false",
            "value_type": "boolean",
            "description": "是否启用维护模式",
            "group": "系统设置",
            "is_public": True,
            "is_system": True,
            "order": 100
        },
        {
            "key": "contact_info",
            "value": json.dumps({
                "phone": "123-456-7890",
                "email": "contact@example.com",
                "address": "某省某市某区某街道"
            }),
            "value_type": "json",
            "description": "联系信息",
            "group": "内容设置",
            "is_public": True,
            "is_system": False,
            "order": 90
        }
    ]
    
    try:
        conn = Tortoise.get_connection("default")
        # 检查settings表是否为空
        count = await conn.execute_query_dict("SELECT COUNT(*) as count FROM settings")
        
        # 如果表不为空且不是强制重新生成，则不添加默认设置
        if int(count[0]["count"]) > 0:
            db_logger.info("系统设置表已有数据，跳过初始化")
            return
        
        # 添加默认设置
        for setting_data in default_settings:
            setting = Setting(**setting_data)
            await setting.save()
            db_logger.info(f"已添加设置: {setting_data['key']}")
        
        db_logger.info("系统设置初始化完成")
    except Exception as e:
        db_logger.error(f"初始化系统设置时出错: {str(e)}")


async def get_redis() -> redis.Redis:
    """
    获取Redis连接
    """
    return redis.Redis(connection_pool=redis_pool)


async def close_db_connections() -> None:
    """
    关闭数据库连接
    """
    db_logger.info("正在关闭数据库连接...")
    await Tortoise.close_connections()
    
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
    
    db_logger.info("数据库连接已关闭") 