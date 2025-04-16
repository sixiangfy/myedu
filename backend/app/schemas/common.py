from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List, Any
from datetime import datetime

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    """标准API响应模型"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="状态消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(..., description="响应时间戳")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: List[T] = Field(..., description="数据项列表")
    total: int = Field(..., description="总数据量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数据量")
    total_pages: int = Field(..., description="总页数")

class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = Field(None, description="错误字段")
    message: str = Field(..., description="错误消息")
    code: str = Field(..., description="错误代码")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="状态消息")
    errors: List[ErrorDetail] = Field([], description="错误详情列表")
    timestamp: datetime = Field(..., description="响应时间戳") 