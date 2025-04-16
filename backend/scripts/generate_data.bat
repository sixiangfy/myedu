@echo off
echo 开始生成教务管理系统测试数据...
cd %~dp0..
python -m scripts.generate_test_data
echo.
echo 数据生成完成！
pause 