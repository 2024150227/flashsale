#!/usr/bin/env python3
"""Database initialization script"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import engine, Base
from app.models.product import Product
from app.models.order import Order
# 初始化数据库,创建表并添加测试商品,如果数据库为空,则添加测试商品
# 连接数据库引擎engine
def init_database():
    print("Initializing database...")
    
    try:
        # 创建数据库表,如果表不存在则创建
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal
        # 获取数据库连接
        db = SessionLocal()
        
        # 检查数据库是否为空
        # 如果数据库为空,则添加测试商品
        existing_product = db.query(Product).first()
        if not existing_product:
            test_product = Product(
                name="Flash Sale - iPhone 15 Pro",
                price=5999.00,
                stock=100,
                description="Limited time flash sale!"
            )
            db.add(test_product)
            db.commit()
            print("Test product added!")
        
        db.close()
        print("Database initialization completed!")
        
    except Exception as e:
        print("Database initialization failed:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    init_database()