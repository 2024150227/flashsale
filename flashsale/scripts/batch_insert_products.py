#!/usr/bin/env python3
"""Batch insert 200 test products to the database"""
#脚本批量插入200个测试商品到数据库
import datetime
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.product import Product

# 生成200个测试商品并插入数据库
# 连接数据库引擎engine
def generate_products():
    print("Starting to insert 200 products...")

    db = SessionLocal()

    try:
        product_templates = [
            ("iPhone 15 Pro Max", 9999.00),
            ("MacBook Pro 14-inch", 15999.00),
            ("iPad Pro 12.9-inch", 9299.00),
            ("Apple Watch Ultra 2", 6499.00),
            ("AirPods Pro 2", 1899.00),
            ("Samsung Galaxy S24 Ultra", 9699.00),
            ("Huawei Mate 60 Pro", 6999.00),
            ("Xiaomi 14 Ultra", 6499.00),
            ("OPPO Find X7 Pro", 5999.00),
            ("vivo X100 Pro", 5499.00),
            ("Sony WH-1000XM5", 2499.00),
            ("Nintendo Switch OLED", 2299.00),
            ("PlayStation 5", 3899.00),
            ("Xbox Series X", 3899.00),
            ("DJI Mini 4 Pro", 5988.00),
            ("Dyson V15 Vacuum", 5499.00),
            ("Philips Air Fryer", 1299.00),
            ("Xiaomi Robot Vacuum", 2999.00),
            ("Huawei Router BE7", 599.00),
            ("Xiaomi Router AX9000", 999.00),
        ]

        products_to_add = []

        for i in range(200):
            template = product_templates[i % len(product_templates)]
            name = f"{template[0]} - Flash Sale #{i+1:03d}"
            price = round(template[1] * random.uniform(0.7, 0.95), 2)
            stock = random.randint(10, 500)
            description = f"Limited time flash sale item, stock is limited! Product #{i+1}."
            #设置created_at和updated_at时间戳字段
            created_at = datetime.datetime.now()
            updated_at = datetime.datetime.now()
            
            product = Product(
                name=name,
                price=price,
                stock=stock,
                description=description,
                is_active=1,
                created_at=created_at,
                updated_at=updated_at
            )
            products_to_add.append(product)

        db.bulk_save_objects(products_to_add)
        db.commit()

        count = db.query(Product).count()
        print(f"Success! Inserted 200 products.")
        print(f"Total products in database: {count}")

    except Exception as e:
        print(f"Failed to insert products: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_products()