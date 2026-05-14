from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
#获取Pydantic模型，用于定义商品的请求和响应数据
from app.schemas.product import Product, ProductCreate
from app.services.product_service import ProductService
from app.utils.sales_rank import get_sales_rank, get_product_sales, get_product_rank
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

# 销量排行榜接口
@router.get("/sales-rank/", response_model=List[Dict])
async def get_sales_rankings(top_n: int = Query(10, ge=1, le=100)):
    """获取商品销量排行榜
    参数：
        top_n: 返回前多少名，默认10，范围1-100
    返回：
        List[Dict]: 包含商品ID和销量的列表，按销量降序排列
    """
    rank_data = get_sales_rank(top_n)
    result = []
    for product_id, sales in rank_data:
        product = product_service.get_product_by_id(product_id)
        if product:
            result.append({
                "product_id": product_id,
                "name": product.name,
                "price": float(product.price),
                "sales": sales,
                "rank": len(result) + 1
            })
    return result

# 获取单个商品销量
@router.get("/{product_id}/sales/", response_model=Dict)
async def get_product_sales_info(product_id: int):
    """获取商品销量信息
    参数：
        product_id: 商品ID
    返回：
        Dict: 包含销量和排名的信息
    """
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    sales = get_product_sales(product_id)
    rank = get_product_rank(product_id)
    
    return {
        "product_id": product_id,
        "name": product.name,
        "sales": sales,
        "rank": rank
    }