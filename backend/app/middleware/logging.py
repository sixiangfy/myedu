import time
from uuid import uuid4
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message

from app.core.logging import get_access_logger

# 获取访问日志记录器
access_logger = get_access_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件，记录每个请求的访问信息
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid4())
        # 添加请求ID到请求状态中
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()
            
        # 记录请求日志
        access_logger.info(
            f"Request started: {request.method} {request.url.path} - ID: {request_id} - "
            f"Client: {client_host} - Params: {dict(request.query_params)}"
        )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 计算请求处理时间
        process_time = time.time() - start_time
        
        # 记录响应日志
        access_logger.info(
            f"Request completed: {request.method} {request.url.path} - ID: {request_id} - "
            f"Status: {response.status_code} - Time: {process_time:.4f}s"
        )
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求正文日志中间件，记录请求体和响应体内容
    注意：此中间件可能会导致性能下降，建议仅在开发环境中使用
    """
    def __init__(
        self, 
        app: ASGIApp, 
        log_request_body: bool = False, 
        log_response_body: bool = False,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否需要跳过日志记录
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return await call_next(request)
        
        # 获取请求ID
        request_id = getattr(request.state, "request_id", str(uuid4()))
        
        # 记录请求体
        if self.log_request_body:
            body = await request.body()
            if body:
                try:
                    access_logger.debug(f"Request body [ID: {request_id}]: {body.decode()}")
                except UnicodeDecodeError:
                    access_logger.debug(f"Request body [ID: {request_id}]: (binary data)")
                # 重置请求体，以便后续处理
                await request._body_reset(body)
        
        # 处理请求
        if self.log_response_body:
            # 自定义响应发送处理
            async def send_wrapper(message: Message):
                if message["type"] == "http.response.body":
                    body = message.get("body", b"")
                    if body:
                        try:
                            access_logger.debug(f"Response body [ID: {request_id}]: {body.decode()}")
                        except UnicodeDecodeError:
                            access_logger.debug(f"Response body [ID: {request_id}]: (binary data)")
                await response_send(message)
                
            # 保存原始send函数
            response = await call_next(request)
            response_send = response.background.send
            response.background.send = send_wrapper
        else:
            response = await call_next(request)
            
        return response


def setup_logging_middleware(app: FastAPI, log_bodies: bool = False, exclude_paths: list = None):
    """
    设置日志中间件
    
    Args:
        app: FastAPI应用
        log_bodies: 是否记录请求体和响应体
        exclude_paths: 排除日志记录的路径列表
    """
    # 添加基本请求日志中间件
    app.add_middleware(LoggingMiddleware)
    
    # 添加请求体和响应体日志中间件（如果启用）
    if log_bodies:
        app.add_middleware(
            RequestLoggingMiddleware, 
            log_request_body=True, 
            log_response_body=True,
            exclude_paths=exclude_paths or ["/docs", "/redoc", "/openapi.json", "/static"]
        ) 