"""Redis 缓存预热服务"""
import json
from app.db.session import SessionLocal
from app.models.product import Product
from app.utils.redis_client import redis_client
from app.core.logger import cache_warmup_logger as logger

# Redis 缓存键前缀
PRODUCTS_CACHE_KEY = "flashsale:products:all"
PRODUCT_CACHE_KEY_PREFIX = "flashsale:product:"

def warmup_products_cache():
    """预热商品数据到 Redis 缓存"""
    logger.info("开始执行 Redis 缓存预热...")
    
    db = SessionLocal()
    try:
        # 从数据库查询所有有效商品
        products = db.query(Product).filter(Product.is_active == 1).all()
        
        if not products:
            logger.warning("数据库中没有找到有效商品，跳过缓存预热")
            return
        
        # 将商品数据写入 Redis
        products_data = []
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
            products_data.append(product_dict)
            
            # 同时设置单个商品缓存（5分钟过期）
            cache_key = f"{PRODUCT_CACHE_KEY_PREFIX}{product.id}"
            redis_client.setex(cache_key, 300, json.dumps(product_dict))
            
            # 设置库存键
            redis_client.set(f"flashsale:stock:{product.id}", product.stock)
        
        # 设置商品列表缓存（5分钟过期）
        redis_client.setex(PRODUCTS_CACHE_KEY, 300, json.dumps(products_data))
        
        logger.info(f"Redis 缓存预热完成，共预热 {len(products)} 个商品")
        
    except Exception as e:
        logger.error(f"Redis 缓存预热失败: {str(e)}")
        raise
    finally:
        db.close()

def is_cache_warmed_up() -> bool:
    """检查缓存是否已预热"""
    return redis_client.get(PRODUCTS_CACHE_KEY) is not None