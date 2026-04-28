from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate
from app.db.session import SessionLocal
import datetime

class ProductService:
    def get_products(self) -> List[Product]:
        """获取所有秒杀商品"""
        """获取所有秒杀商品"""
        db = SessionLocal()
        try:
            products = db.query(Product).filter(Product.is_active == 1).all()
            return products
        finally:
            db.close()

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID获取商品详情"""
        db = SessionLocal()
        try:
            return db.query(Product).filter(
                Product.id == product_id,
                Product.is_active == 1
            ).first()
        finally:
            db.close()

    def create_product(self, product_data: ProductCreate) -> Product:
        """创建新商品"""
        db = SessionLocal()
        try:
            db_product = Product(
                name=product_data.name,
                price=product_data.price,
                stock=product_data.stock,
                description=product_data.description,
                is_active=product_data.is_active
            )
            db.add(db_product)
            db.commit()
            db.refresh(db_product)
            return db_product
        finally:
            db.close()