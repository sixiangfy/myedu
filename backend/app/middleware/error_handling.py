import traceback
from typing import Callable, Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

# 获取错误日志记录器
error_logger = get_logger("error")


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    错误日志中间件，捕获并记录请求处理过程中的异常
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # 获取请求ID
            request_id = getattr(request.state, "request_id", "unknown")
            
            # 记录详细错误信息
            error_logger.error(
                f"Unhandled exception in request [ID: {request_id}]: "
                f"{request.method} {request.url.path}\n"
                f"Exception: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # 返回JSON错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id
                }
            )


class APIExceptionHandler:
    """
    全局API异常处理器
    """
    def __init__(self, app: FastAPI):
        self.app = app
        self.setup_exception_handlers()
    
    def setup_exception_handlers(self):
        # 注册全局异常处理
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception) -> Response:
            # 获取请求ID
            request_id = getattr(request.state, "request_id", "unknown")
            
            # 记录详细错误信息
            error_logger.error(
                f"Exception in request [ID: {request_id}]: "
                f"{request.method} {request.url.path}\n"
                f"Exception: {str(exc)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            # 返回JSON错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "message": str(exc),
                    "request_id": request_id
                }
            )


def setup_error_handling(app: FastAPI):
    """
    设置错误处理
    
    Args:
        app: FastAPI应用
    """
    # 添加错误日志中间件
    app.add_middleware(ErrorLoggingMiddleware)
    
    # 添加全局异常处理
    APIExceptionHandler(app) 