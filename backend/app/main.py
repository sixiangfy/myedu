from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.db.init_db import init_db, close_db_connections

# 设置日志
logger = setup_logging(log_level="DEBUG")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="教务管理系统API",
    version="1.0.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    swagger_ui_parameters={
        "docExpansion": "none",
        "defaultModelsExpandDepth": 0,
        "operationsSorter": "alpha",
        "tagsSorter": "alpha",
        "defaultModelRendering": "model",
        "filter": True,
        "syntaxHighlight.theme": "monokai",
        "persistAuthorization": True,
    },
    contact={
        "name": "技术支持",
        "email": "support@example.com",
    },
    terms_of_service="",
    license_info={
        "name": "内部使用",
        "url": "https://example.com/license",
    },
    openapi_tags=[
        {
            "name": "认证",
            "description": "用户认证相关接口，包括登录和刷新令牌"
        },
        {
            "name": "用户管理",
            "description": "用户账号管理接口，包括新增、修改和删除用户"
        },
        {
            "name": "学生管理",
            "description": "学生信息管理接口"
        },
        {
            "name": "教师管理",
            "description": "教师信息管理接口"
        },
        {
            "name": "班级管理",
            "description": "班级管理相关接口"
        },
        {
            "name": "年级管理",
            "description": "年级管理相关接口"
        },
        {
            "name": "科目管理",
            "description": "学科管理相关接口"
        },
        {
            "name": "考试管理",
            "description": "考试管理相关接口"
        },
        {
            "name": "成绩管理",
            "description": "学生成绩管理接口"
        },
        {
            "name": "成绩分析",
            "description": "成绩数据分析和统计接口"
        }
    ]
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库连接"""
    logger.info("应用程序启动中...")
    try:
        # 使用generate_only=True参数确保不会删除现有数据
        await init_db(generate_only=True)
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭数据库连接"""
    logger.info("应用程序关闭中...")
    await close_db_connections()
    logger.info("应用程序已关闭")

@app.get("/")
async def root():
    return {"message": "教务管理系统API服务正在运行"} 