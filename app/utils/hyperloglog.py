from app.utils.redis_client import redis_client
from typing import Optional

class HyperLogLogService:
    """
    Redis HyperLogLog 服务
    用于高效统计基数（去重后的元素数量）
    特点：空间效率极高（约12KB），精度约0.81%误差
    """
    
    def __init__(self, key_prefix: str = "flashsale:hll"):
        self.key_prefix = key_prefix
    
    def get_key(self, name: str) -> str:
        """生成完整的 Redis Key"""
        return f"{self.key_prefix}:{name}"
    
    def add(self, name: str, *values: str):
        """
        向 HyperLogLog 添加元素
        
        Args:
            name: HLL名称
            values: 要添加的元素（支持多个）
        """
        key = self.get_key(name)
        redis_client.pfadd(key, *values)
    
    def count(self, name: str) -> int:
        """
        获取 HyperLogLog 的基数估算值
        
        Args:
            name: HLL名称
        
        Returns:
            int: 估算的基数（去重后的元素数量）
        """
        key = self.get_key(name)
        return redis_client.pfcount(key)
    
    def merge(self, dest_name: str, *src_names: str):
        """
        合并多个 HyperLogLog 到目标 HLL
        
        Args:
            dest_name: 目标HLL名称
            src_names: 源HLL名称列表
        """
        dest_key = self.get_key(dest_name)
        src_keys = [self.get_key(name) for name in src_names]
        redis_client.pfmerge(dest_key, *src_keys)
    
    def delete(self, name: str):
        """
        删除 HyperLogLog
        
        Args:
            name: HLL名称
        """
        key = self.get_key(name)
        redis_client.delete(key)


# 秒杀场景常用的 HLL 函数

# 商品访问UV统计: hll:product:view:{product_id}
# 统计商品详情页的独立访客数

def record_product_view(product_id: int, user_id: int):
    """记录用户访问商品"""
    key = f"flashsale:hll:product:view:{product_id}"
    redis_client.pfadd(key, str(user_id))

def get_product_view_uv(product_id: int) -> int:
    """获取商品访问UV"""
    key = f"flashsale:hll:product:view:{product_id}"
    return redis_client.pfcount(key)


# 活动访问UV统计: hll:activity:{activity_id}
# 统计秒杀活动的独立访客数

def record_activity_view(activity_id: int, user_id: int):
    """记录用户访问活动"""
    key = f"flashsale:hll:activity:{activity_id}"
    redis_client.pfadd(key, str(user_id))

def get_activity_view_uv(activity_id: int) -> int:
    """获取活动访问UV"""
    key = f"flashsale:hll:activity:{activity_id}"
    return redis_client.pfcount(key)


# 每日访问UV统计: hll:daily:{date}
# 统计每日独立访客数

def record_daily_visit(user_id: int, date: str = None):
    """记录用户每日访问"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:hll:daily:{date}"
    redis_client.pfadd(key, str(user_id))

def get_daily_uv(date: str = None) -> int:
    """获取每日UV"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:hll:daily:{date}"
    return redis_client.pfcount(key)


# 合并多日UV统计

def merge_daily_uvs(start_date: str, end_date: str, dest_name: str = "merged"):
    """
    合并指定日期范围的UV数据
    
    Args:
        start_date: 开始日期（格式：YYYYMMDD）
        end_date: 结束日期（格式：YYYYMMDD）
        dest_name: 合并后的HLL名称
    
    Returns:
        int: 合并后的UV总数
    """
    from datetime import datetime, timedelta
    
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    src_keys = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        src_keys.append(f"flashsale:hll:daily:{date_str}")
        current += timedelta(days=1)
    
    dest_key = f"flashsale:hll:{dest_name}"
    if src_keys:
        redis_client.pfmerge(dest_key, *src_keys)
        return redis_client.pfcount(dest_key)
    return 0
