from app.utils.redis_client import redis_client
from typing import List, Tuple

# 销量排行榜的 Redis Key
SALES_RANK_KEY = "flashsale:sales:rank"

def update_sales_rank(product_id: int, increment: int = 1):
    """
    更新商品销量排行（ZSet）
    
    Args:
        product_id: 商品ID
        increment: 销量增量，默认为1
    """
    try:
        # ZINCRBY：增量更新分数（销量）
        redis_client.zincrby(SALES_RANK_KEY, increment, product_id)
        return True
    except Exception as e:
        print(f"更新销量排行失败: {e}")
        return False

def get_sales_rank(top_n: int = 10) -> List[Tuple[int, int]]:
    """
    获取销量排行榜前N名
    
    Args:
        top_n: 返回前多少名，默认10
        
    Returns:
        List[(product_id, sales)]: 商品ID和销量的列表，按销量降序排列
    """
    try:
        # ZREVRANGE：按分数降序获取前N个元素，包含分数
        result = redis_client.zrevrange(SALES_RANK_KEY, 0, top_n - 1, withscores=True)
        # 转换为 (product_id, sales) 元组列表
        return [(int(item[0]), int(item[1])) for item in result]
    except Exception as e:
        print(f"获取销量排行失败: {e}")
        return []

def get_product_sales(product_id: int) -> int:
    """
    获取单个商品的销量
    
    Args:
        product_id: 商品ID
        
    Returns:
        int: 销量，不存在返回0
    """
    try:
        sales = redis_client.zscore(SALES_RANK_KEY, product_id)
        return int(sales) if sales else 0
    except Exception as e:
        print(f"获取商品销量失败: {e}")
        return 0

def get_product_rank(product_id: int) -> int:
    """
    获取商品的销量排名
    
    Args:
        product_id: 商品ID
        
    Returns:
        int: 排名（从1开始），不存在返回0
    """
    try:
        # ZREVRANK：获取降序排名（0-based）
        rank = redis_client.zrevrank(SALES_RANK_KEY, product_id)
        return rank + 1 if rank is not None else 0
    except Exception as e:
        print(f"获取商品排名失败: {e}")
        return 0

def clear_sales_rank():
    """
    清空销量排行榜
    """
    try:
        redis_client.delete(SALES_RANK_KEY)
        return True
    except Exception as e:
        print(f"清空销量排行失败: {e}")
        return False
