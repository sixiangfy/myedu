import logging
import sys
from typing import List

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


def setup_logging(log_level: str = "INFO", modules: List[str] = None):
    """
    配置日志系统
    
    :param log_level: 日志级别
    :param modules: 需要捕获日志的模块列表
    """
    # 移除所有默认处理器
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # 设置要捕获的模块日志
    modules = modules or ["uvicorn", "uvicorn.error", "fastapi", "tortoise", "app"]
    for module in modules:
        logging.getLogger(module).handlers = [InterceptHandler()]
        logging.getLogger(module).propagate = False

    # 配置loguru
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "level": log_level,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
            }
        ]
    )
    
    return logger 