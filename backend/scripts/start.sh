#!/bin/bash

# 启动应用程序
echo "正在启动教务管理系统API..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 