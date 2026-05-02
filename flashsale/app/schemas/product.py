from pydantic import BaseModel
from typing import Optional
import datetime
# 基础商品模型，包含商品的基本信息，后面的模型继承自这个模型
# 1. 商品名称
# 2. 商品价格
# 3. 商品库存
# 4. 商品描述（可选）
# 5. 商品是否激活（默认激活）
#作用是定义商品的基本信息，用于创建和更新商品时传递数据
class ProductBase(BaseModel):
    name:str
    price:float
    stock:int
    description:Optional[str]=None
    is_active:int=1
class ProductCreate(ProductBase):
    pass 
class Product(ProductBase):
    id: int
    # 商品创建时间（可选，兼容旧数据）
    created_at: Optional[datetime.datetime] = None
    # 商品更新时间（可选，兼容旧数据）
    updated_at: Optional[datetime.datetime] = None
    # 商品是否激活（默认激活）
    is_active: int = 1
    class Config:
        from_attributes = True