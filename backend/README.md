# 教务管理系统

基于FastAPI和Tortoise-ORM开发的教务管理系统后端API

## 功能特点

- 完整的用户管理（教师、学生、管理员）
- 课程管理
- 班级管理
- 成绩管理
- JWT认证
- Redis缓存
- Tortoise-ORM数据库操作

## 项目结构

```
app/
├── api/                    # API路由
│   ├── dependencies/       # API依赖项（认证等）
│   └── v1/                 # API v1路由
│       └── endpoints/      # API端点
├── core/                   # 核心配置
├── crud/                   # 数据库CRUD操作
├── db/                     # 数据库初始化和连接
├── models/                 # 数据模型
├── schemas/                # Pydantic模型
└── services/               # 业务服务层
```

## 安装和运行

1. 克隆项目

```bash
git clone <repository-url>
cd edu-management
```

2. 创建并激活虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 创建`.env`文件并设置环境变量

```
# 数据库配置
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=edu_db
DB_PORT=5432

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 安全配置
SECRET_KEY=your_secret_key
```

5. 运行应用

```bash
uvicorn app.main:app --reload
```

6. 访问API文档

打开浏览器访问 http://localhost:8000/docs

## 开发

### 添加新模型

1. 在`app/models/`目录下创建新模型文件
2. 在`app/models/__init__.py`中注册新模型
3. 在`app/schemas/`目录下创建相应的Pydantic模型
4. 在`app/crud/`目录下创建CRUD操作类
5. 在`app/api/v1/endpoints/`目录下创建API端点

## 贡献

欢迎提交Pull Request或Issue

## 许可证

MIT 