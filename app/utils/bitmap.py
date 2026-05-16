from app.utils.redis_client import redis_client
from typing import List
from datetime import datetime

class BitmapService:
    """
    Redis Bitmap 服务
    用于高效存储和查询大量布尔状态
    
    当前主要用途：每日签到功能
    使用 user_id 作为 bit 位偏移量，日期作为 key 后缀
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


# ==================== 每日签到功能 ====================
# 数据结构: flashsale:bitmap:checkin:{date}
# 使用 user_id 作为 bit 位偏移量来记录用户签到状态

def mark_checkin(user_id: int, date: str = None):
    """
    标记用户签到
    
    Args:
        user_id: 用户ID（作为bit位偏移量）
        date: 日期，格式 YYYYMMDD，默认为今天
    """
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    redis_client.setbit(key, user_id, 1)

def has_checkin(user_id: int, date: str = None) -> bool:
    """
    检查用户是否签到
    
    Args:
        user_id: 用户ID
        date: 日期，格式 YYYYMMDD，默认为今天
    
    Returns:
        bool: 是否已签到
    """
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    return bool(redis_client.getbit(key, user_id))

def get_checkin_count(date: str = None) -> int:
    """
    获取指定日期的签到人数
    
    Args:
        date: 日期，格式 YYYYMMDD，默认为今天
    
    Returns:
        int: 签到人数
    """
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    key = f"flashsale:bitmap:checkin:{date}"
    return redis_client.bitcount(key)

def get_user_checkin_days(user_id: int, start_date: str, end_date: str) -> int:
    """
    统计用户在指定日期范围内的签到天数
    
    Args:
        user_id: 用户ID
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
    
    Returns:
        int: 签到天数
    """
    count = 0
    current_date = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    while current_date <= end:
        date_str = current_date.strftime("%Y%m%d")
        if has_checkin(user_id, date_str):
            count += 1
        current_date += datetime.timedelta(days=1)
    
    return count

def get_continuous_checkin_days(user_id: int) -> int:
    """
    获取用户连续签到天数
    
    Args:
        user_id: 用户ID
    
    Returns:
        int: 连续签到天数
    """
    count = 0
    today = datetime.now()
    
    for i in range(365):
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        if has_checkin(user_id, date_str):
            count += 1
        else:
            break
    
    return count