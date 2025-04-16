#!/bin/bash
echo "开始生成教务管理系统测试数据..."
cd "$(dirname "$0")/.."
python -m scripts.generate_test_data
echo ""
echo "数据生成完成！"
read -p "按Enter键退出..." key 