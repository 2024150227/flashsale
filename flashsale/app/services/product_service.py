from typing import List, Optional
from app.models.product import Product
from app.utils.redis_client import redis_client

class ProductService:
    def get_products(self) -> List[Product]:
        """获取所有秒杀商品"""
        # 这里可以从Redis缓存中获取，或者从数据库中查询
        # 暂时返回模拟数据
        return [
            Product(
                id=1001,
                name="iPhone 14 Pro",
                price=7999.0,
                stock=100,
                description="最新款iPhone",
                is_active=1
            ),
            Product(
                id=1002,
                name="MacBook Pro",
                price=12999.0,
                stock=50,
                description="高性能笔记本电脑",
                is_active=1
            )
        ]
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID获取商品详情"""
        # 优先从Redis缓存中获取
        # 暂时返回模拟数据
        if product_id == 1001:
            return Product(
                id=1001,
                name="iPhone 14 Pro",
                price=7999.0,
                stock=100,
                description="最新款iPhone",
                is_active=1
            )
        elif product_id == 1002:
            return Product(
                id=1002,
                name="MacBook Pro",
                price=12999.0,
                stock=50,
                description="高性能笔记本电脑",
                is_active=1
            )
        return None