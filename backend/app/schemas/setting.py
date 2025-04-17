from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import json


class SettingBase(BaseModel):
    """设置基础Schema"""
    key: str = Field(..., description="设置键名")
    value: Optional[str] = Field(None, description="设置值")
    value_type: str = Field("string", description="值类型: string, number, boolean, json")
    description: Optional[str] = Field(None, description="设置描述")
    group: Optional[str] = Field(None, description="设置分组")
    is_public: bool = Field(False, description="是否公开")
    is_system: bool = Field(False, description="是否为系统设置")
    order: int = Field(0, description="排序")


class SettingCreate(SettingBase):
    """创建设置Schema"""
    pass


class SettingUpdate(BaseModel):
    """更新设置Schema"""
    value: Optional[str] = Field(None, description="设置值")
    description: Optional[str] = Field(None, description="设置描述")
    group: Optional[str] = Field(None, description="设置分组")
    is_public: Optional[bool] = Field(None, description="是否公开")
    order: Optional[int] = Field(None, description="排序")


class SettingInDB(SettingBase):
    """数据库中的设置Schema"""
    id: int

    class Config:
        orm_mode = True


class Setting(SettingInDB):
    """响应的设置Schema"""
    typed_value: Optional[Any] = None

    @validator('typed_value', pre=True, always=True)
    def set_typed_value(cls, v, values):
        """根据value_type转换value的类型"""
        if 'value' not in values or values['value'] is None:
            return None

        value = values['value']
        value_type = values.get('value_type', 'string')

        if value_type == 'number':
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except ValueError:
                return 0
        elif value_type == 'boolean':
            return value.lower() in ('true', '1', 't', 'y', 'yes')
        elif value_type == 'json':
            try:
                return json.loads(value)
            except:
                return {}
        else:  # string
            return value


class SettingListResponse(BaseModel):
    """设置列表响应"""
    items: List[Setting]
    total: int 