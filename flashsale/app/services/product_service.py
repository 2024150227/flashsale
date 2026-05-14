from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate
from app.db.session import SessionLocal
import datetime
from app.core.logger import product_service_logger as logger
from app.core.xss import escape_html
from app.utils.redis_client import redis_client
#业务逻辑层，负责处理商品相关的业务逻辑
class ProductService:
    def get_products(self) -> List[Product]:
        """获取所有秒杀商品"""
        db = SessionLocal()
        try:
            # 从数据库查询所有秒杀商品,is_active为1表示商品有效
            products = db.query(Product).filter(Product.is_active == 1).all()
            
            # 从 Redis 读取最新库存覆盖
            for product in products:
                redis_stock = redis_client.get(f"flashsale:stock:{product.id}")
                if redis_stock is not None:
                    product.stock = int(redis_stock)
            
            return products
        finally:
            db.close()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID获取商品详情
        权重：1（低频率，但最重要）
        参数：
            product_id: 商品ID
        返回：
            Product: 商品详情
        异常处理：
            404: 商品不存在，返回404错误
        """
        db = SessionLocal()
        try:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.is_active == 1
            ).first()
            
            # 从 Redis 读取最新库存覆盖
            if product:
                redis_stock = redis_client.get(f"flashsale:stock:{product_id}")
                if redis_stock is not None:
                    product.stock = int(redis_stock)
            
            return product
        finally:
            db.close()

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
            return db_product
        finally:
            db.close()