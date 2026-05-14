from typing import List, Optional
import json
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate
from app.db.session import SessionLocal
import datetime
from app.core.logger import product_service_logger as logger
from app.core.xss import escape_html
from app.utils.redis_client import redis_client

# Redis 缓存键前缀
PRODUCTS_CACHE_KEY = "flashsale:products:all"
PRODUCT_CACHE_KEY_PREFIX = "flashsale:product:"

#业务逻辑层，负责处理商品相关的业务逻辑
class ProductService:
    def get_products(self) -> List[Product]:
        """获取所有秒杀商品（先查Redis，再查MySQL）"""
        # 1. 先尝试从 Redis 获取缓存
        cached_data = redis_client.get(PRODUCTS_CACHE_KEY)
        if cached_data:
            logger.debug("从Redis缓存获取商品列表")
            # 解析缓存数据
            products_data = json.loads(cached_data)
            return [self._dict_to_product(p) for p in products_data]
        
        # 2. Redis 查不到，从 MySQL 查询
        logger.debug("从MySQL数据库获取商品列表")
        db = SessionLocal()
        try:
            products = db.query(Product).filter(Product.is_active == 1).all()
            
            # 3. 将数据写入 Redis 缓存（5分钟过期）
            products_data = [self._product_to_dict(p) for p in products]
            redis_client.setex(PRODUCTS_CACHE_KEY, 300, json.dumps(products_data))
            
            return products
        finally:
            db.close()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID获取商品详情（先查Redis，再查MySQL）
        权重：1（低频率，但最重要）
        参数：
            product_id: 商品ID
        返回：
            Product: 商品详情
        异常处理：
            404: 商品不存在，返回404错误
        """
        # 1. 先尝试从 Redis 获取缓存
        cache_key = f"{PRODUCT_CACHE_KEY_PREFIX}{product_id}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"从Redis缓存获取商品ID: {product_id}")
            return self._dict_to_product(json.loads(cached_data))
        
        # 2. Redis 查不到，从 MySQL 查询
        logger.debug(f"从MySQL数据库获取商品ID: {product_id}")
        db = SessionLocal()
        try:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.is_active == 1
            ).first()
            
            # 3. 将数据写入 Redis 缓存（5分钟过期）
            if product:
                redis_client.setex(cache_key, 300, json.dumps(self._product_to_dict(product)))
            
            return product
        finally:
            db.close()

    def _product_to_dict(self, product: Product) -> dict:
        """将 Product 对象转换为字典"""
        return {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "description": product.description,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }

    def _dict_to_product(self, data: dict) -> Product:
        """将字典转换为 Product 对象"""
        product = Product(
            id=data["id"],
            name=data["name"],
            price=data["price"],
            stock=data["stock"],
            description=data.get("description"),
            is_active=data["is_active"]
        )
        if data.get("created_at"):
            product.created_at = datetime.datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            product.updated_at = datetime.datetime.fromisoformat(data["updated_at"])
        return product

    def create_product(self, product_data: ProductCreate) -> Product:
        """创建新商品
        权重：1（低频率，但最重要）
        参数：
            product_data: 商品创建信息（JSON格式）
        返回：
            Product: 创建成功的商品信息
        异常处理：
            400: 商品库存不足，返回400错误
            其他: 记录失败日志
        """
        db = SessionLocal()
        try:
            db_product = Product(
                name=escape_html(product_data.name),
                price=product_data.price,
                stock=product_data.stock,
                description=escape_html(product_data.description) if product_data.description else None,
                is_active=product_data.is_active
            )
            db.add(db_product)
            db.commit()
            db.refresh(db_product)
            
            # 清除缓存，下次查询会重新加载
            redis_client.delete(PRODUCTS_CACHE_KEY)
            
            return db_product
        finally:
            db.close()
    
    def update_product_stock(self, product_id: int, new_stock: int):
        """更新商品库存（同时更新数据库和Redis）"""
        db = SessionLocal()
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.stock = new_stock
                db.commit()
                
                # 更新 Redis 缓存中的库存
                cache_key = f"{PRODUCT_CACHE_KEY_PREFIX}{product_id}"
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    product_data = json.loads(cached_data)
                    product_data["stock"] = new_stock
                    redis_client.setex(cache_key, 300, json.dumps(product_data))
                
                # 更新库存键
                redis_client.set(f"flashsale:stock:{product_id}", new_stock)
            
            return product
        finally:
            db.close()
    
    def clear_cache(self):
        """清除所有商品缓存"""
        redis_client.delete(PRODUCTS_CACHE_KEY)
        logger.info("已清除商品列表缓存")