#!/usr/bin/env python3
"""
商品缓存预热脚本

功能：在指定时间（默认2小时后）将商品信息从数据库同步到Redis，
用于秒杀场景的缓存预热，减轻数据库压力。
# 模块导入：os、sys、time、json、logging、SessionLocal、Product、get_redis_client
"""

import os
import sys
import time
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.product import Product
from app.core.security import get_redis_client


def get_all_products(db):
    """
    从数据库获取所有活跃商品
    """
    logger.info("开始从数据库获取商品信息...")
    products = db.query(Product).filter(Product.is_active == 1).all()
    
    product_list = []
    for product in products:
        product_dict = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "description": product.description,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        }
        product_list.append(product_dict)
    
    print(f"成功获取 {len(product_list)} 个商品")
    return product_list


def cache_products_to_redis(products):
    """
    将商品信息缓存到Redis
    """
    redis = get_redis_client()
    if not redis:
        print("无法连接到Redis")
        return False
    
    try:
        # 存储商品列表
        print("开始缓存商品信息到Redis...")
        
        # 存储所有商品列表（用于列表页）
        products_json = json.dumps(products)
        redis.setex("flashsale:products", 24 * 60 * 60, products_json)  # 24小时过期
        print("已缓存商品列表")
        
        # 存储单个商品（用于详情页，方便快速查找）
        for product in products:
            product_key = f"flashsale:product:{product['id']}"
            redis.setex(product_key, 24 * 60 * 60, json.dumps(product))
        
        # 存储库存（秒杀场景需要快速获取库存）
        for product in products:
            stock_key = f"flashsale:stock:{product['id']}"
            redis.setex(stock_key, 24 * 60 * 60, product['stock'])

        from datetime import datetime
        redis.set("flashsale:start_time", datetime.now().isoformat())

        print(f"成功缓存 {len(products)} 个商品到Redis")
        return True
    
    except Exception as e:
        print(f"缓存商品到Redis失败: {str(e)}")
        return False


def main(wait_hours: float = 2.0):
    """
    主函数：等待指定时间后执行缓存预热
    
    参数:
        wait_hours: 等待小时数，默认0小时
    """
    wait_seconds = wait_hours * 3600
    
    print("=" * 60)
    print("商品缓存预热脚本启动")
    print(f"将在 {wait_hours} 小时后执行缓存预热")
    print(f"等待时间: {int(wait_seconds)} 秒")
    print("=" * 60)
    
    # 等待指定时间
    start_time = time.time()
    while time.time() - start_time < wait_seconds:
        remaining = int(wait_seconds - (time.time() - start_time))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60
        print(f"\r剩余等待时间: {hours}小时 {minutes}分钟 {seconds}秒", end='', flush=True)
        time.sleep(1)
    
    print("等待时间到")  # 换行
    print("开始执行缓存预热...")
    
    # 获取数据库连接
    db = SessionLocal()
    
    try:
        # 获取商品信息
        products = get_all_products(db)
        
        if not products:
            print("数据库中没有商品，跳过缓存预热")
            return
        
        # 缓存到Redis
        success = cache_products_to_redis(products)
        
        if success:
            print("=" * 60)
            print("✅ 缓存预热完成！")
            print("=" * 60)
        else:
            print("=" * 60)
            print("❌ 缓存预热失败！")
            print("=" * 60)
    
    except Exception as e:
        print(f"缓存预热过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    # 可以通过命令行参数指定等待时间（小时）
    wait_time = 0.0
    if len(sys.argv) > 1:
        try:
            wait_time = float(sys.argv[1])
            print(f"命令行指定等待时间: {wait_time} 小时")
        except ValueError:
            print(f"无效的等待时间参数: {sys.argv[1]}，使用默认值 {wait_time} 小时")
    
    main(wait_time)