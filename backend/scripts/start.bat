@echo off
echo 正在启动教务管理系统API...
echo 确保MySQL和Redis服务已经启动

REM 切换到项目根目录
cd ..

REM 如果需要安装依赖，请取消下面这行的注释
REM pip install -r requirements.txt

REM 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 