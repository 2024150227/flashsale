import redis
from app.core.config import settings

# 初始化Redis客户端
redis_client = redis.StrictRedis(
    host=settings.redis_url.split("//")[1].split(":")[0],
    port=int(settings.redis_url.split(":")[-1].split("/")[0]),
    db=int(settings.redis_url.split("/")[-1]),
    decode_responses=True
)

# 预热库存
def warmup_stock(product_id: int, initial_stock: int):
    """预热库存到Redis"""
    redis_client.set(f"stock:product:{product_id}", initial_stock)