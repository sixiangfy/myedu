# 教务管理系统API接口优化方案

## 一、接口路径规范化

### 1. 统一API版本控制
所有接口路径从 `/api/` 改为 `/api/v1/`，与后端目录结构 `app/api/v1/` 保持一致。

### 2. RESTful风格调整
| 原接口路径 | 优化后路径 | 说明 |
|------------|------------|------|
| `/api/auth/login` | `/api/v1/auth/token` | 获取访问令牌 |
| `/api/auth/refresh_token` | `/api/v1/auth/token/refresh` | 刷新访问令牌 |
| `/api/auth/logout` | `/api/v1/auth/token/revoke` | 注销访问令牌 |
| `/api/auth/forgot_password` | `/api/v1/auth/password/reset` | 重置密码 |
| `/api/auth/send_verify_code` | `/api/v1/auth/verify-code` | 发送验证码 |
| `/api/auth/change_password` | `/api/v1/auth/password/change` | 修改密码 |
| `/api/grades/batch_delete` | `/api/v1/grades/batch` | 批量删除年级 |
| `/api/classes/batch_delete` | `/api/v1/classes/batch` | 批量删除班级 |
| `/api/subjects/batch_delete` | `/api/v1/subjects/batch` | 批量删除学科 |
| `/api/teachers/batch_delete` | `/api/v1/teachers/batch` | 批量删除教师 |
| `/api/students/batch_delete` | `/api/v1/students/batch` | 批量删除学生 |
| `/api/exams/batch_delete` | `/api/v1/exams/batch` | 批量删除考试 |
| `/api/scores/batch_delete` | `/api/v1/scores/batch` | 批量删除成绩 |
| `/api/notices/batch_read` | `/api/v1/notices/batch/read` | 批量标记通知为已读 |

## 二、响应格式标准化

### 1. 统一响应结构
```json
{
  "code": 200,                    // 状态码
  "message": "success",           // 状态信息
  "data": {                       // 响应数据
    "items": [],                  // 数据列表
    "total": 0,                   // 总数
    "page": 1,                    // 当前页
    "page_size": 20,              // 每页数量
    "total_pages": 1              // 总页数
  },
  "timestamp": "2024-01-01T00:00:00Z"  // 时间戳
}
```

### 2. 统一错误响应
```json
{
  "code": 400,
  "message": "Bad Request",
  "errors": [
    {
      "field": "username",
      "message": "用户名不能为空",
      "code": "REQUIRED_FIELD"
    }
  ],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 3. 状态码定义
| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求格式正确但语义错误 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

## 三、认证机制完善

### 1. Token刷新机制
在 `app/core/security.py` 中实现：
```python
async def refresh_access_token(refresh_token: str) -> dict:
    """刷新访问令牌"""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # 检查刷新令牌是否在黑名单中
        if await is_token_blacklisted(refresh_token):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        # 创建新的访问令牌
        access_token = create_access_token(data={"sub": user_id})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
```

### 2. Token黑名单机制
在 `app/core/security.py` 中添加：
```python
async def add_token_to_blacklist(token: str, expires_in: int) -> None:
    """将令牌加入黑名单"""
    await redis_client.setex(f"blacklist:{token}", expires_in, "1")

async def is_token_blacklisted(token: str) -> bool:
    """检查令牌是否在黑名单中"""
    return await redis_client.exists(f"blacklist:{token}")
```

### 3. 登录失败次数限制
在 `app/services/auth.py` 中实现：
```python
async def check_login_attempts(phone: str) -> bool:
    """检查登录尝试次数"""
    attempts = await redis_client.get(f"login_attempts:{phone}")
    if attempts and int(attempts) >= 5:
        return False
    return True

async def increment_login_attempts(phone: str) -> None:
    """增加登录尝试次数"""
    await redis_client.incr(f"login_attempts:{phone}")
    await redis_client.expire(f"login_attempts:{phone}", 3600)  # 1小时后过期

async def reset_login_attempts(phone: str) -> None:
    """重置登录尝试次数"""
    await redis_client.delete(f"login_attempts:{phone}")
```

## 四、参数验证规范

### 1. 请求参数验证
在 `app/schemas/` 目录下定义请求模型，例如 `app/schemas/auth.py`：
```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class LoginRequest(BaseModel):
    phone: str = Field(..., description="手机号", example="13800138000", min_length=11, max_length=11)
    password: str = Field(..., description="密码", example="123456", min_length=6, max_length=20)
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v.isdigit():
            raise ValueError('手机号必须是数字')
        return v
```

### 2. 响应模型定义
在 `app/schemas/` 目录下定义响应模型，例如 `app/schemas/common.py`：
```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional
from datetime import datetime

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")

class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="状态信息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
```

## 五、文件上传下载规范

### 1. 文件上传限制
在 `app/api/v1/students.py` 中实现：
```python
@router.post("/import", response_model=ImportResponse)
async def import_students(
    file: UploadFile = File(..., description="Excel文件"),
    current_user: User = Depends(get_current_user)
):
    """批量导入学生"""
    # 检查文件大小
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    while chunk := await file.read(chunk_size):
        file_size += len(chunk)
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="文件大小超过限制")
    
    # 检查文件类型
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="只支持Excel文件")
    
    # 处理文件上传
    # ...
```

### 2. 文件下载进度
在 `app/utils/excel.py` 中实现：
```python
async def generate_excel_file(data: List[Dict], filename: str) -> StreamingResponse:
    """生成Excel文件并返回流式响应"""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # 写入数据
    # ...
    
    workbook.close()
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

## 六、缓存策略

### 1. 接口缓存
在 `app/api/deps.py` 中实现：
```python
from functools import wraps
from app.utils.redis import redis_client

def cache_response(expire: int = 300):
    """缓存响应结果"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"cache:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            await redis_client.setex(cache_key, expire, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

### 2. 缓存更新策略
在 `app/services/` 中实现：
```python
async def update_cache_on_data_change(cache_key_pattern: str) -> None:
    """数据变更时更新缓存"""
    keys = await redis_client.keys(cache_key_pattern)
    if keys:
        await redis_client.delete(*keys)
```

## 七、安全性增强

### 1. 接口访问频率限制
在 `app/core/security.py` 中实现：
```python
async def check_rate_limit(ip: str, endpoint: str, limit: int = 60, period: int = 60) -> bool:
    """检查接口访问频率"""
    key = f"rate_limit:{ip}:{endpoint}"
    count = await redis_client.incr(key)
    
    if count == 1:
        await redis_client.expire(key, period)
    
    return count <= limit
```

### 2. 敏感数据加密
在 `app/utils/security.py` 中实现：
```python
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str) -> str:
    """加密敏感数据"""
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(data.encode()).decode()

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """解密敏感数据"""
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(encrypted_data.encode()).decode()
```

## 八、错误处理完善

### 1. 错误码定义
在 `app/core/exceptions.py` 中定义：
```python
from enum import Enum

class ErrorCode(str, Enum):
    # 通用错误码
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # 认证相关错误码
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    
    # 业务相关错误码
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    GRADE_ALREADY_EXISTS = "GRADE_ALREADY_EXISTS"
    CLASS_ALREADY_EXISTS = "CLASS_ALREADY_EXISTS"
    SUBJECT_ALREADY_EXISTS = "SUBJECT_ALREADY_EXISTS"
    STUDENT_ALREADY_EXISTS = "STUDENT_ALREADY_EXISTS"
    EXAM_ALREADY_EXISTS = "EXAM_ALREADY_EXISTS"
```

### 2. 全局异常处理
在 `app/main.py` 中实现：
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import ErrorCode

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "errors": [{"message": exc.detail, "code": "HTTP_ERROR"}],
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # 记录未处理的异常
    logger.exception("Unhandled exception")
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "Internal Server Error",
            "errors": [{"message": str(exc), "code": ErrorCode.UNKNOWN_ERROR}],
            "timestamp": datetime.now().isoformat()
        }
    )
```

## 九、接口文档格式

### 1. OpenAPI规范
在 `app/main.py` 中配置：
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="教务管理系统API",
    description="教务管理系统后端API接口文档",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="教务管理系统API",
        version="1.0.0",
        description="教务管理系统后端API接口文档",
        routes=app.routes,
    )
    
    # 自定义安全方案
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## 十、业务逻辑优化

### 1. 成绩分析接口增强
在 `app/api/v1/analysis.py` 中添加：
```python
@router.get("/student/performance", response_model=StudentPerformanceResponse)
async def get_student_performance(
    student_id: int,
    exam_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取学生成绩表现分析"""
    # 实现学生成绩表现分析逻辑
    # 包括成绩分布、与班级/年级平均分对比、进步情况等
    pass

@router.get("/class/performance", response_model=ClassPerformanceResponse)
async def get_class_performance(
    class_id: int,
    exam_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取班级成绩表现分析"""
    # 实现班级成绩表现分析逻辑
    # 包括成绩分布、与年级平均分对比、进步情况等
    pass
```

### 2. 数据导出格式选择
在 `app/api/v1/students.py` 中实现：
```python
@router.get("/export")
async def export_students(
    format: str = Query("xlsx", description="导出格式", enum=["xlsx", "csv", "pdf"]),
    grade_id: Optional[int] = None,
    class_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """导出学生数据"""
    # 根据format参数选择不同的导出格式
    if format == "xlsx":
        return await export_students_to_excel(grade_id, class_id)
    elif format == "csv":
        return await export_students_to_csv(grade_id, class_id)
    elif format == "pdf":
        return await export_students_to_pdf(grade_id, class_id)
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")
```

## 十一、性能优化建议

### 1. 数据库查询优化
在 `app/services/` 中实现：
```python
async def get_paginated_data(
    model,
    page: int = 1,
    page_size: int = 20,
    filters: dict = None,
    order_by: str = None
):
    """获取分页数据，优化查询性能"""
    # 构建查询
    query = model.filter(**filters) if filters else model
    
    # 添加排序
    if order_by:
        query = query.order_by(order_by)
    
    # 计算总数
    total = await query.count()
    
    # 分页查询
    items = await query.offset((page - 1) * page_size).limit(page_size)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
```

### 2. 大数据量处理策略
在 `app/services/` 中实现：
```python
async def process_large_dataset(data: List[Dict], batch_size: int = 1000):
    """处理大数据集，分批处理"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        await process_batch(batch)
```

## 十二、监控和日志

### 1. 接口调用日志
在 `app/utils/logging.py` 中实现：
```python
import logging
import time
from fastapi import Request

logger = logging.getLogger("api")

async def log_request_middleware(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"status_code={response.status_code} "
        f"process_time={process_time:.4f}s"
    )
    
    return response
```

### 2. 性能监控
在 `app/utils/monitoring.py` 中实现：
```python
from prometheus_client import Counter, Histogram
import time

# 定义指标
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

async def monitor_request(request: Request, call_next):
    """请求监控中间件"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # 记录请求计数
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    # 记录请求延迟
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response
```

## 总结

以上优化方案结合了后端目录结构，对API接口进行了全面优化，主要包括：

1. 接口路径规范化，与后端目录结构保持一致
2. 响应格式标准化，统一成功和错误响应
3. 认证机制完善，增加Token刷新和黑名单机制
4. 参数验证规范，使用Pydantic模型进行验证
5. 文件上传下载规范，增加文件限制和进度反馈
6. 缓存策略，实现接口缓存和缓存更新
7. 安全性增强，增加访问频率限制和敏感数据加密
8. 错误处理完善，定义错误码和全局异常处理
9. 接口文档格式，使用OpenAPI规范
10. 业务逻辑优化，增强成绩分析接口
11. 性能优化建议，优化数据库查询和大数据处理
12. 监控和日志，实现接口调用日志和性能监控

这些优化将使API接口更加规范、安全、高效，并提供更好的开发体验。 