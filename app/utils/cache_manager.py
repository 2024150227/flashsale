import json
import random
from app.core.security import get_redis_client

# 缓存过期时间配置
BASE_EXPIRE = 24 * 60 * 60  # 基础过期时间：24小时
OFFSET_RANGE = 60 * 60  # 随机偏移范围：±1小时


def update_product_cache(product_id: int, product_data: dict):
    """
    更新单个商品缓存（带随机偏移）
    
    Args:
        product_id: 商品ID
        product_data: 商品数据字典
    
    Returns:
        bool: 是否成功
    """
    redis = get_redis_client()
    if not redis:
        return False
    
    try:
        product_key = f"flashsale:product:{product_id}"
        # 添加随机偏移防止缓存雪崩
        expire_time = BASE_EXPIRE + random.randint(-OFFSET_RANGE, OFFSET_RANGE)
        redis.setex(product_key, expire_time, json.dumps(product_data))
        print(f"✅ 已更新商品 {product_id} 的缓存，过期时间: {expire_time // 3600}小时")
        return True
    except Exception as e:
        print(f"❌ 更新商品缓存失败: {str(e)}")
        return False


def update_stock_cache(product_id: int, stock: int):
    """
    更新商品库存缓存（带随机偏移）
    
    Args:
        product_id: 商品ID
        stock: 新库存数量
    
    Returns:
        bool: 是否成功
    """
    redis = get_redis_client()
    if not redis:
        return False
    
    try:
        stock_key = f"flashsale:stock:{product_id}"
        # 添加随机偏移防止缓存雪崩
        expire_time = BASE_EXPIRE + random.randint(-OFFSET_RANGE, OFFSET_RANGE)
        redis.setex(stock_key, expire_time, stock)
        print(f"✅ 已更新商品 {product_id} 的库存: {stock}，过期时间: {expire_time // 3600}小时")
        return True
    except Exception as e:
        print(f"❌ 更新库存缓存失败: {str(e)}")
        return False


def invalidate_product_cache(product_id: int):
    """
    失效单个商品缓存（删除）
    
    Args:
        product_id: 商品ID
    
    Returns:
        bool: 是否成功
    """
    redis = get_redis_client()
    if not redis:
        return False
    
    try:
        product_key = f"flashsale:product:{product_id}"
        stock_key = f"flashsale:stock:{product_id}"
        
        pipe = redis.pipeline()
        pipe.delete(product_key)
        pipe.delete(stock_key)
        pipe.execute()
        
        print(f"✅ 已删除商品 {product_id} 的缓存")
        return True
    except Exception as e:
        print(f"❌ 删除商品缓存失败: {str(e)}")
        return False


def refresh_all_products_cache(products: list):
    """
    刷新所有商品缓存（批量更新，带随机偏移）
    
    Args:
        products: 商品列表
    
    Returns:
        bool: 是否成功
    """
    redis = get_redis_client()
    if not redis:
        return False
    
    try:
        pipe = redis.pipeline()
        
        # 商品列表带随机偏移
        products_json = json.dumps(products)
        expire_time = BASE_EXPIRE + random.randint(-OFFSET_RANGE, OFFSET_RANGE)
        pipe.setex("flashsale:products", expire_time, products_json)
        
        # 每个商品带不同的随机偏移
        for product in products:
            product_key = f"flashsale:product:{product['id']}"
            expire_time = BASE_EXPIRE + random.randint(-OFFSET_RANGE, OFFSET_RANGE)
            pipe.setex(product_key, expire_time, json.dumps(product))
            
            stock_key = f"flashsale:stock:{product['id']}"
            expire_time = BASE_EXPIRE + random.randint(-OFFSET_RANGE, OFFSET_RANGE)
            pipe.setex(stock_key, expire_time, product['stock'])
        
        pipe.execute()
        print(f"✅ 已刷新 {len(products)} 个商品的缓存（带随机偏移）")
        return True
    except Exception as e:
        print(f"❌ 刷新商品缓存失败: {str(e)}")
        return False
