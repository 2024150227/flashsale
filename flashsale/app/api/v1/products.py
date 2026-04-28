from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.product import Product, ProductCreate
from app.services.product_service import ProductService

router = APIRouter()
product_service = ProductService()

@router.get("/", response_model=List[Product])
async def get_products():
    """获取所有秒杀商品"""
    return product_service.get_products()

@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """获取商品详情"""
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

@router.post("/", response_model=Product)
async def create_product(product: ProductCreate):
    """创建秒杀商品"""
    return product_service.create_product(product)