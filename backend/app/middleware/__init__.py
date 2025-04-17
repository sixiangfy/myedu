from fastapi import FastAPI
from app.middleware.logging import setup_logging_middleware
from app.middleware.error_handling import setup_error_handling


def setup_middlewares(app: FastAPI, log_bodies: bool = False):
    """
    设置所有中间件
    
    Args:
        app: FastAPI应用
        log_bodies: 是否记录请求体和响应体
    """
    # 设置日志中间件
    setup_logging_middleware(app, log_bodies=log_bodies)
    
    # 设置错误处理中间件
    setup_error_handling(app) 