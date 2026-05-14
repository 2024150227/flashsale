from app.utils.redis_client import redis_client
from typing import List

class BitmapService:
    """
    Redis Bitmap 服务
    用于高效存储和查询大量布尔状态
    """

    def __init__(self, key_prefix: str = "flashsale:bitmap"):
        self.key_prefix = key_prefix

    def get_key(self, name: str) -> str:
        """生成完整的 Redis Key"""
        return f"{self.key_prefix}:{name}"

    def set_bit(self, name: str, offset: int, value: bool = True):
        """
        设置指定位的值

        Args:
            name: bitmap名称
            offset: 位偏移量（用户ID等）
            value: True=1, False=0
        """
        key = self.get_key(name)
        redis_client.setbit(key, offset, 1 if value else 0)

    def get_bit(self, name: str, offset: int) -> bool:
        """
        获取指定位的值

        Args:
            name: bitmap名称
            offset: 位偏移量

        Returns:
            bool: 该位的值
        """
        key = self.get_key(name)
        return bool(redis_client.getbit(key, offset))

    def count_bits(self, name: str) -> int:
        """
        统计值为1的位数

        Args:
            name: bitmap名称

        Returns:
            int: 值为1的位数
        """
        key = self.get_key(name)
        return redis_client.bitcount(key)

    def get_range(self, name: str, start: int, end: int) -> List[bool]:
        """
        获取指定范围的位值

        Args:
            name: bitmap名称
            start: 起始偏移量
            end: 结束偏移量

        Returns:
            List[bool]: 位值列表
        """
        key = self.get_key(name)
        result = redis_client.getbit(key, start)
        # Redis没有直接获取范围的命令，需要逐个获取
        return [self.get_bit(name, i) for i in range(start, end + 1)]

    def bit_operation(self, dest_name: str, operation: str, *src_names: str):
        """
        位图运算（AND/OR/XOR/NOT）

        Args:
            dest_name: 目标bitmap名称
            operation: 运算类型（AND/OR/XOR）
            src_names: 源bitmap名称列表
        """
        dest_key = self.get_key(dest_name)
        src_keys = [self.get_key(name) for name in src_names]

        if operation.upper() == "AND":
            redis_client.bitop("AND", dest_key, *src_keys)
        elif operation.upper() == "OR":
            redis_client.bitop("OR", dest_key, *src_keys)
        elif operation.upper() == "XOR":
            redis_client.bitop("XOR", dest_key, *src_keys)
        else:
            raise ValueError("Unsupported operation. Use AND, OR, or XOR.")

    def clear_bitmap(self, name: str):
        """
        清空bitmap

        Args:
            name: bitmap名称
        """
        key = self.get_key(name)
        redis_client.delete(key)


# 秒杀场景常用的Bitmap实例

# 用户参与秒杀记录: flashsale:bitmap:seckill:{session_id}:product:{product_id}
# 记录哪些用户参与了某场秒杀的商品，用于去重判断

def mark_user_seckill(product_id: int, user_id: int, session_id: int):
    """标记用户参与秒杀（支持场次）"""
    key = f"flashsale:bitmap:seckill:{session_id}:product:{product_id}"
    redis_client.setbit(key, user_id, 1)

def has_user_seckill(product_id: int, user_id: int, session_id: int) -> bool:
    """检查用户是否参与过该场秒杀"""
    key = f"flashsale:bitmap:seckill:{session_id}:product:{product_id}"
    return bool(redis_client.getbit(key, user_id))

def get_seckill_participants(product_id: int, session_id: int) -> int:
    """获取某场秒杀参与用户数量"""
    key = f"flashsale:bitmap:seckill:{session_id}:product:{product_id}"
    return redis_client.bitcount(key)


# 每日签到: bitmap:checkin:{date}
# 记录用户每日签到情况

def mark_checkin(user_id: int, date: str = None):
    """标记用户签到"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    redis_client.setbit(key, user_id, 1)

def has_checkin(user_id: int, date: str = None) -> bool:
    """检查用户是否签到"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    return bool(redis_client.getbit(key, user_id))

def get_checkin_count(date: str = None) -> int:
    """获取签到人数"""
    if not date:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    return redis_client.bitcount(key)
