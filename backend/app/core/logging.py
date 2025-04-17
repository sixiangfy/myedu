import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    拦截标准库logging的处理器，将其转发到loguru
    """
    def emit(self, record):
        # 获取对应的loguru级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用者
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(
    log_level: str = "INFO", 
    modules: List[str] = None,
    log_to_file: bool = True,
    log_dir: Optional[str] = None,
    retention: str = "30 days",
    rotation: str = "00:00",
    log_format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        modules: 需要捕获日志的模块列表
        log_to_file: 是否将日志保存到文件
        log_dir: 日志文件目录，默认为backend/logs
        retention: 日志保留时间
        rotation: 日志文件轮转时间
        log_format: 日志格式
    """
    # 移除所有默认处理器
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # 设置要捕获的模块日志
    modules = modules or ["uvicorn", "uvicorn.error", "fastapi", "tortoise", "app"]
    for module in modules:
        logging.getLogger(module).handlers = [InterceptHandler()]
        logging.getLogger(module).propagate = False

    # 配置handlers
    handlers: List[Dict[str, Any]] = [
        {
            "sink": sys.stdout,
            "level": log_level,
            "format": log_format
        }
    ]
    
    # 配置文件日志
    if log_to_file:
        # 确定日志目录
        if log_dir is None:
            # 默认使用backend/logs目录
            base_dir = Path(__file__).parents[2]  # backend目录
            log_dir = str(base_dir / "logs")
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 应用日志
        app_log_file = os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log")
        handlers.append({
            "sink": app_log_file,
            "level": log_level,
            "format": log_format,
            "rotation": rotation,
            "retention": retention,
            "compression": "zip",
            "encoding": "utf-8",
            "enqueue": True,
        })
        
        # 错误日志 - 单独收集错误和警告
        error_log_file = os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log")
        handlers.append({
            "sink": error_log_file,
            "level": "WARNING",
            "format": log_format,
            "rotation": rotation,
            "retention": retention,
            "compression": "zip",
            "encoding": "utf-8",
            "enqueue": True,
        })
        
        # 访问日志 - 单独收集接口访问日志
        access_log_file = os.path.join(log_dir, "access_{time:YYYY-MM-DD}.log")
        handlers.append({
            "sink": access_log_file,
            "level": log_level,
            "format": log_format,
            "rotation": rotation,
            "retention": retention,
            "compression": "zip",
            "encoding": "utf-8",
            "enqueue": True,
            "filter": lambda record: "access" in record["extra"]
        })
        
        # 数据库日志 - 单独收集数据库操作日志
        db_log_file = os.path.join(log_dir, "db_{time:YYYY-MM-DD}.log")
        handlers.append({
            "sink": db_log_file,
            "level": log_level,
            "format": log_format,
            "rotation": rotation,
            "retention": retention,
            "compression": "zip",
            "encoding": "utf-8",
            "enqueue": True,
            "filter": lambda record: any(name in record["name"] for name in ["tortoise", "db", "sql", "orm"])
        })
    
    # 配置loguru
    logger.configure(handlers=handlers)
    
    return logger


def get_logger(name: str = None):
    """获取命名的logger实例"""
    return logger.bind(name=name)


def get_access_logger():
    """获取接口访问日志logger"""
    return logger.bind(access=True)


def get_db_logger():
    """获取数据库操作日志logger"""
    return logger.bind(name="db") 