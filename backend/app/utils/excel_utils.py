import io
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from fastapi import UploadFile, HTTPException, status
import xlrd
import datetime

class ExcelUtils:
    """Excel导入导出工具类"""
    
    @staticmethod
    async def read_excel(file: UploadFile) -> pd.DataFrame:
        """
        读取Excel文件
        
        Args:
            file: 上传的Excel文件
        
        Returns:
            pd.DataFrame: 读取的数据框
        """
        try:
            # 获取文件内容
            contents = await file.read()
            
            # 根据文件扩展名判断使用哪个引擎
            file_ext = file.filename.split('.')[-1].lower()
            if file_ext == 'xlsx':
                engine = 'openpyxl'
            elif file_ext == 'xls':
                engine = 'xlrd'
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不支持的文件格式，只支持.xlsx和.xls格式"
                )
            
            # 读取Excel文件
            df = pd.read_excel(io.BytesIO(contents), engine=engine)
            
            return df
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"读取Excel文件失败: {str(e)}"
            )
    
    @staticmethod
    def write_excel(data: List[Dict[str, Any]], columns: List[Tuple[str, str]], 
                    title: str = None, sheet_name: str = 'Sheet1') -> io.BytesIO:
        """
        生成Excel文件
        
        Args:
            data: 要写入的数据列表
            columns: 列名和标题的元组列表，例如 [('id', 'ID'), ('name', '姓名')]
            title: 标题（可选）
            sheet_name: 工作表名称（可选）
        
        Returns:
            io.BytesIO: Excel文件的字节流
        """
        try:
            # 创建字节流
            output = io.BytesIO()
            
            # 提取列的键和标题
            column_keys = [col[0] for col in columns]
            column_titles = [col[1] for col in columns]
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 确保所有列都存在，如果不存在则添加空列
            for key in column_keys:
                if key not in df.columns:
                    df[key] = None
            
            # 只保留需要的列，并按指定顺序排列
            df = df[column_keys]
            
            # 重命名列
            df.columns = column_titles
            
            # 使用xlsxwriter引擎创建Excel
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # 如果有标题，从第2行开始写入数据
                start_row = 1 if title else 0
                df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=start_row)
                
                # 获取工作表和工作簿
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                
                # 设置标题格式
                if title:
                    title_format = workbook.add_format({
                        'bold': True,
                        'font_size': 14,
                        'align': 'center',
                        'valign': 'vcenter'
                    })
                    # 合并单元格并写入标题
                    worksheet.merge_range(f'A1:{chr(65+len(columns)-1)}1', title, title_format)
                
                # 设置标题行格式
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D7E4BC',
                    'border': 1
                })
                
                # 应用标题行格式
                for col_num, value in enumerate(column_titles):
                    worksheet.write(start_row, col_num, value, header_format)
                
                # 调整列宽
                for i, col in enumerate(column_titles):
                    max_len = max(
                        len(str(col)),
                        df.iloc[:, i].astype(str).map(len).max() if not df.empty else 0
                    )
                    worksheet.set_column(i, i, min(max_len + 2, 30))
            
            # 重置字节流位置
            output.seek(0)
            
            return output
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"生成Excel文件失败: {str(e)}"
            )
    
    @staticmethod
    def validate_data(df: pd.DataFrame, required_columns: List[str], 
                     validators: Dict[str, callable] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        验证导入的数据
        
        Args:
            df: 要验证的数据框
            required_columns: 必填列
            validators: 验证函数字典，键为列名，值为验证函数
        
        Returns:
            Tuple[bool, List[Dict]]: 是否通过验证和错误信息列表
        """
        # 初始化结果
        is_valid = True
        errors = []
        
        # 检查列是否存在
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            is_valid = False
            errors.append({
                "type": "missing_columns",
                "message": f"缺少必填列: {', '.join(missing_columns)}"
            })
            return is_valid, errors
        
        # 检查数据是否为空
        if df.empty:
            is_valid = False
            errors.append({
                "type": "empty_data",
                "message": "Excel文件中没有数据"
            })
            return is_valid, errors
        
        # 检查空值
        for col in required_columns:
            null_indices = df[df[col].isnull()].index.tolist()
            if null_indices:
                is_valid = False
                for idx in null_indices:
                    row_num = idx + 2  # Excel行号从1开始，标题行是第1行
                    errors.append({
                        "type": "null_value",
                        "message": f"第{row_num}行的'{col}'不能为空",
                        "row": int(row_num),
                        "column": col
                    })
        
        # 应用自定义验证器
        if validators:
            for col, validator in validators.items():
                if col in df.columns:
                    for idx, value in enumerate(df[col]):
                        if pd.notna(value):  # 只验证非空值
                            try:
                                result = validator(value)
                                if result is not True:  # 验证失败
                                    is_valid = False
                                    row_num = idx + 2
                                    errors.append({
                                        "type": "validation_error",
                                        "message": f"第{row_num}行的'{col}'验证失败: {result}",
                                        "row": int(row_num),
                                        "column": col,
                                        "value": value
                                    })
                            except Exception as e:
                                is_valid = False
                                row_num = idx + 2
                                errors.append({
                                    "type": "validation_error",
                                    "message": f"第{row_num}行的'{col}'验证失败: {str(e)}",
                                    "row": int(row_num),
                                    "column": col,
                                    "value": value
                                })
        
        return is_valid, errors 