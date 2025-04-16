# 教务管理系统后端目录结构

## 技术栈
- FastAPI
- Tortoise-ORM
- MySQL
- Redis
- JWT Token OAuth2 认证

## 目录结构
```
backend/
├── app/                      # 应用主目录
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置文件
│   ├── database.py          # Tortoise-ORM 数据库连接配置
│   │
│   ├── models/              # Tortoise-ORM 模型
│   │   ├── __init__.py
│   │   ├── user.py          # 用户模型
│   │   ├── grade.py         # 年级模型
│   │   ├── class.py         # 班级模型
│   │   ├── subject.py       # 学科模型
│   │   ├── teacher.py       # 教师模型
│   │   ├── student.py       # 学生模型
│   │   ├── exam.py          # 考试模型
│   │   ├── score.py         # 成绩模型
│   │   ├── notice.py        # 通知公告模型
│   │   └── system_log.py    # 系统日志模型
│   │
│   ├── schemas/             # Pydantic 模型（请求/响应模型）
│   │   ├── __init__.py
│   │   ├── user.py          # 用户数据验证
│   │   ├── grade.py         # 年级数据验证
│   │   ├── class.py         # 班级数据验证
│   │   ├── subject.py       # 学科数据验证
│   │   ├── teacher.py       # 教师数据验证
│   │   ├── student.py       # 学生数据验证
│   │   ├── exam.py          # 考试数据验证
│   │   ├── score.py         # 成绩数据验证
│   │   ├── notice.py        # 通知公告数据验证
│   │   └── system_log.py    # 系统日志数据验证
│   │
│   ├── api/                 # API路由
│   │   ├── __init__.py
│   │   ├── v1/             # API版本控制
│   │   │   ├── __init__.py
│   │   │   ├── auth.py     # 认证相关接口
│   │   │   ├── users.py    # 用户管理接口
│   │   │   ├── grades.py   # 年级管理接口
│   │   │   ├── classes.py  # 班级管理接口
│   │   │   ├── subjects.py # 学科管理接口
│   │   │   ├── teachers.py # 教师管理接口
│   │   │   ├── students.py # 学生管理接口
│   │   │   ├── exams.py    # 考试管理接口
│   │   │   ├── scores.py   # 成绩管理接口
│   │   │   └── notices.py  # 通知公告接口
│   │   └── deps.py         # 依赖注入（认证等）
│   │
│   ├── core/               # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py     # JWT相关
│   │   ├── config.py       # 配置管理
│   │   └── exceptions.py   # 异常处理
│   │
│   ├── services/           # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth.py         # 认证服务
│   │   ├── user.py         # 用户服务
│   │   ├── grade.py        # 年级服务
│   │   ├── class.py        # 班级服务
│   │   ├── subject.py      # 学科服务
│   │   ├── teacher.py      # 教师服务
│   │   ├── student.py      # 学生服务
│   │   ├── exam.py         # 考试服务
│   │   ├── score.py        # 成绩服务
│   │   └── notice.py       # 通知公告服务
│   │
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── security.py     # 安全相关工具
│       ├── excel.py        # Excel处理工具
│       └── logging.py      # 日志工具
│
├── tests/                  # 测试文件
│   ├── __init__.py
│   ├── conftest.py        # pytest配置
│   ├── test_api/          # API测试
│   └── test_services/     # 服务测试
│
├── logs/                   # 日志文件
├── .env                    # 环境变量
├── .env.example           # 环境变量示例
├── .gitignore             # Git忽略文件
├── requirements.txt        # 生产环境依赖
├── requirements-dev.txt    # 开发环境依赖
└── README.md              # 项目说明文件
```

## 主要依赖包
### 生产环境依赖 (requirements.txt)
```
fastapi>=0.68.0
uvicorn>=0.15.0
tortoise-orm>=0.19.0
aerich>=0.7.2
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.5
aioredis>=2.0.0
python-dotenv>=0.19.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

### 开发环境依赖 (requirements-dev.txt)
```
pytest>=6.2.5
pytest-asyncio>=0.16.0
httpx>=0.23.0
black>=21.9b0
isort>=5.9.3
flake8>=3.9.2
```

## 关键配置文件说明

### 1. 环境变量 (.env)
```
# 数据库配置
DB_URL=mysql://user:password@localhost:3306/dbname

# Redis配置
REDIS_URL=redis://localhost:6379/0

# JWT配置
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 2. 数据库配置 (app/database.py)
```python
from tortoise import Tortoise
from app.core.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DB_URL},
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
```

### 3. 安全配置 (app/core/security.py)
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT配置
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    # JWT token创建逻辑
    pass

def verify_password(plain_password: str, hashed_password: str):
    # 密码验证逻辑
    pass
```

## 开发规范
1. 所有API路由统一放在 `app/api/v1/` 目录下
2. 数据库模型统一放在 `app/models/` 目录下
3. 数据验证模型统一放在 `app/schemas/` 目录下
4. 业务逻辑统一放在 `app/services/` 目录下
5. 工具函数统一放在 `app/utils/` 目录下
6. 核心配置统一放在 `app/core/` 目录下
7. 所有测试文件统一放在 `tests/` 目录下 