from fastapi import APIRouter, HTTPException
from typing import List
#获取Pydantic模型，用于定义商品的请求和响应数据
from app.schemas.product import Product, ProductCreate
from app.services.product_service import ProductService
from app.core.logger import products_api_logger as logger
#商品路由层，负责处理商品相关的API请求
router = APIRouter()
# 获取所有的秒杀商品
product_service = ProductService()
# 商品列表接口，返回所有秒杀商品的列表
# 商品列表接口，返回所有秒杀商品的列表
@router.get("/", response_model=List[Product])
async def get_products():
    """获取所有秒杀商品
    返回：
        List[Product]: 所有秒杀商品的列表
    """ 
    return product_service.get_products()
# 商品详情接口，返回指定秒杀商品的详细信息
# 商品详情接口，返回指定秒杀商品的详细信息
@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """获取商品详情
    参数：
        product_id: 商品ID
    返回：
        Product: 商品详情
    异常处理：
        404: 商品不存在，返回404错误
    """
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

# 商品创建接口，用于创建新的秒杀商品
@router.post("/", response_model=Product)
async def create_product(product: ProductCreate):
    """创建秒杀商品
    权重：1（低频率，但最重要）
    参数：
        product: 商品创建信息（JSON格式）
    返回：
        Product: 创建成功的商品信息
    异常处理：
        400: 商品库存不足，返回400错误
        其他: 记录失败日志
    """ 
    return product_service.create_product(product)