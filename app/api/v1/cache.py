from fastapi import APIRouter, HTTPException, Query
from app.utils.cache_manager import (
    update_product_cache,
    update_stock_cache,
    invalidate_product_cache,
    refresh_all_products_cache
)
from app.db.session import SessionLocal
from app.models.product import Product

router = APIRouter(prefix="/cache", tags=["cache"])

@router.post("/product/{product_id}")
async def update_single_product_cache(product_id: int):
    """更新单个商品缓存"""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "description": product.description,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
        
        success = update_product_cache(product_id, product_data)
        if success:
            return {"message": f"商品 {product_id} 缓存更新成功"}
        else:
            raise HTTPException(status_code=500, detail="缓存更新失败")
    finally:
        db.close()

@router.post("/stock/{product_id}")
async def update_product_stock_cache(product_id: int, stock: int = Query(..., description="新库存数量")):
    """更新商品库存缓存"""
    success = update_stock_cache(product_id, stock)
    if success:
        return {"message": f"商品 {product_id} 库存缓存更新成功: {stock}"}
    else:
        raise HTTPException(status_code=500, detail="库存缓存更新失败")

@router.delete("/product/{product_id}")
async def delete_product_cache(product_id: int):
    """删除商品缓存"""
    success = invalidate_product_cache(product_id)
    if success:
        return {"message": f"商品 {product_id} 缓存已删除"}
    else:
        raise HTTPException(status_code=500, detail="删除缓存失败")

@router.post("/refresh/all")
async def refresh_all_cache():
    """刷新所有商品缓存"""
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.is_active == 1).all()
        product_list = []
        for product in products:
            product_list.append({
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock,
                "description": product.description,
                "is_active": product.is_active,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            })
        
        success = refresh_all_products_cache(product_list)
        if success:
            return {"message": f"已刷新 {len(product_list)} 个商品的缓存"}
        else:
            raise HTTPException(status_code=500, detail="刷新缓存失败")
    finally:
        db.close()
