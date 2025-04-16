import logging
import redis.asyncio as redis
from tortoise import Tortoise
from tortoise.exceptions import OperationalError

from app.core.config import settings
from app.models import TORTOISE_MODELS

logger = logging.getLogger(__name__)

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


async def drop_tables() -> None:
    """
    删除所有数据表
    """
    logger.info("尝试删除现有数据表...")
    
    table_names = [
        "users", "grades", "classes", "subjects", 
        "teachers", "students", "exams", "scores",
        "class_teacher"  # m2m关系表
    ]
    
    for table in table_names:
        try:
            await Tortoise.get_connection("default").execute_query(f"DROP TABLE IF EXISTS {table}")
            logger.info(f"已删除表: {table}")
        except Exception as e:
            logger.error(f"删除表 {table} 失败: {str(e)}")


async def init_tortoise(generate_only: bool = True) -> None:
    """
    初始化Tortoise-ORM
    
    Args:
        generate_only: 如果为True，只生成表结构而不删除现有表；如果为False，先删除再创建
    """
    logger.info("正在初始化Tortoise-ORM...")
    
    # 使用MySQL连接
    await Tortoise.init(
        db_url=settings.DATABASE_URI,
        modules={"models": TORTOISE_MODELS},
    )
    
    # 如果不是仅生成模式，则先删除现有表
    if not generate_only:
        await drop_tables()
    
    # 生成数据库schema
    logger.info("正在生成数据库模式...")
    try:
        # 根据generate_only参数决定使用哪种方式生成schema
        if generate_only:
            # 使用safe=True只创建不存在的表
            await Tortoise.generate_schemas(safe=True)
            logger.info("数据库模式生成完成(安全模式，保留现有数据)")
        else:
            # 使用safe=False强制重新创建表
            await Tortoise.generate_schemas(safe=False)
            logger.info("数据库模式生成完成(强制模式，已清空数据)")
    except OperationalError as e:
        logger.error(f"生成数据库模式时出错: {str(e)}")
        # 尝试使用safe=True
        logger.info("尝试使用安全模式生成数据库模式...")
        await Tortoise.generate_schemas(safe=True)
        logger.info("数据库模式生成完成(安全模式)")
    
    logger.info("Tortoise-ORM初始化完成")


async def init_redis() -> None:
    """
    初始化Redis连接
    """
    global redis_pool
    
    logger.info("正在初始化Redis连接...")
    try:
        redis_url = settings.REDIS_URI
        logger.info(f"Redis连接URL: {redis_url}")
        redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True
        )
        # 测试连接
        test_conn = redis.Redis(connection_pool=redis_pool)
        await test_conn.ping()
        logger.info("Redis连接测试成功")
    except Exception as e:
        logger.error(f"Redis连接失败: {str(e)}")
        raise
    logger.info("Redis连接初始化完成")


async def get_redis() -> redis.Redis:
    """
    获取Redis连接
    """
    return redis.Redis(connection_pool=redis_pool)


async def close_db_connections() -> None:
    """
    关闭数据库连接
    """
    logger.info("正在关闭数据库连接...")
    await Tortoise.close_connections()
    
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
    
    logger.info("数据库连接已关闭") 